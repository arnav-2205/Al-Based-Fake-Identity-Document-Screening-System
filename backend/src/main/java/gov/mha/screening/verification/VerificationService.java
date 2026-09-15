package gov.mha.screening.verification;

import com.fasterxml.jackson.databind.ObjectMapper;
import gov.mha.screening.ai.AiClient;
import gov.mha.screening.ai.AiDtos;
import gov.mha.screening.audit.AuditService;
import gov.mha.screening.blacklist.BlacklistService;
import gov.mha.screening.blockchain.BlockchainService;
import gov.mha.screening.common.ApiException;
import gov.mha.screening.common.HashUtil;
import gov.mha.screening.config.AppProperties;
import gov.mha.screening.document.Document;
import gov.mha.screening.document.DocumentService;
import gov.mha.screening.document.MinioStorageService;
import gov.mha.screening.extraction.ExtractedData;
import gov.mha.screening.extraction.ExtractedDataRepository;
import gov.mha.screening.notification.NotificationService;
import gov.mha.screening.risk.RiskEngine;
import gov.mha.screening.security.CurrentUser;
import gov.mha.screening.validation.ValidationEngine;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

@Service
@Slf4j
@RequiredArgsConstructor
public class VerificationService {

    private final DocumentService documentService;
    private final MinioStorageService storage;
    private final AiClient aiClient;
    private final ExtractedDataRepository extractedRepo;
    private final VerificationRepository verificationRepo;
    private final FaceEmbeddingRepository embeddingRepo;
    private final ValidationEngine validationEngine;
    private final BlacklistService blacklistService;
    private final RiskEngine riskEngine;
    private final AuditService auditService;
    private final BlockchainService blockchain;
    private final NotificationService notificationService;
    private final CurrentUser currentUser;
    private final AppProperties props;
    private final ObjectMapper objectMapper;

    /** ELA heatmaps are large and demo-only — kept in memory, not in Postgres. */
    private final Map<Long, String> heatmaps = new ConcurrentHashMap<>();

    @Transactional
    public VerificationDtos.VerificationView start(Long documentId, byte[] liveFaceImage, String ip) {
        Document doc = documentService.require(documentId);
        byte[] docImage = storage.get(doc.getFileReference());

        // ---- 4. parallel AI inference ----------------------------------
        AiDtos.AiBundle ai = aiClient.analyzeAll(docImage, liveFaceImage);

        // ---- 5. structured extraction --------------------------------
        ExtractedData extracted = buildExtracted(doc, ai.ocr());
        extracted = extractedRepo.save(extracted);
        if (doc.getDocumentNumber() == null && extracted.getPassportNumber() != null) {
            doc.setDocumentNumber(extracted.getPassportNumber());
            documentService.save(doc);
        }
        if (ai.ocr() != null) {
            String detectedType = ai.ocr().documentSubtype() != null ? ai.ocr().documentSubtype()
                    : (ai.ocr().detectedDocumentType() != null ? ai.ocr().detectedDocumentType()
                    : (ai.ocr().visualZone() != null && ai.ocr().visualZone().get("detectedDocumentType") != null
                    ? String.valueOf(ai.ocr().visualZone().get("detectedDocumentType")) : null));
            if (detectedType != null && !"UNKNOWN".equalsIgnoreCase(detectedType)) {
                doc.setDocumentType(detectedType);
                documentService.save(doc);
            }
        }

        // ---- 6. deterministic validation -----------------------------
        ValidationEngine.Outcome validation = validationEngine.validate(extracted, ai.ocr());

        // ---- 7. blacklist lookup ------------------------------------
        BlacklistService.Hit blacklist = blacklistService.check(
                extracted.getPassportNumber(), extracted.getName(), extracted.getDateOfBirth());

        // ---- tamper composite ------------------------------------
        double tamperComposite = compositeTamper(ai.tamper());
        AiDtos.PhotoForgeryResult pf = ai.tamper() != null ? ai.tamper().photoForgery() : null;
        boolean photoForgerySuspicious = pf != null && "SUSPICIOUS".equalsIgnoreCase(pf.status());

        AiDtos.TextManipulationResult tm = ai.tamper() != null ? ai.tamper().textManipulation() : null;
        boolean textManipulationSuspicious = tm != null && "SUSPICIOUS".equalsIgnoreCase(tm.status());

        AiDtos.StampForgeryResult sf = ai.tamper() != null ? ai.tamper().stampForgery() : null;
        boolean stampForgerySuspicious = sf != null && "SUSPICIOUS".equalsIgnoreCase(sf.status());

        AiDtos.MetadataAnalysisResult ma = ai.tamper() != null ? ai.tamper().metadataAnalysis() : null;
        boolean metadataSuspicious = ma != null && "SUSPICIOUS".equalsIgnoreCase(ma.status());

        boolean facePerformed = liveFaceImage != null
                && ai.face() != null && ai.face().faceMatchScore() != null
                && !"UNKNOWN".equalsIgnoreCase(String.valueOf(ai.face().faceMatchStatus()));
        boolean livenessFailed = ai.face() != null && "SPOOF".equalsIgnoreCase(String.valueOf(ai.face().livenessStatus()));

        // ---- 8. multi-identity check (only performed when live face photo supplied) ----
        MultiIdentity multi = facePerformed
                ? checkMultiIdentity(ai.face(), extracted, doc.getId())
                : new MultiIdentity(false, "NO_LIVE_FACE_SUPPLIED", null, 0.0);

        boolean vizMrzMismatch = validation.vizMrzCrossValidation() != null
                && "MISMATCH".equalsIgnoreCase(validation.vizMrzCrossValidation().status());

        // ---- 9. risk scoring -----------------------------------
        RiskEngine.Input riskInput = new RiskEngine.Input(
                tamperComposite,
                faceScore(ai.face()),
                validation.failed(),
                blacklist.matched(),
                multi.flagged(),
                livenessFailed,
                facePerformed,
                photoForgerySuspicious,
                textManipulationSuspicious,
                vizMrzMismatch,
                validation.expiryValidation(),
                stampForgerySuspicious,
                metadataSuspicious);

        RiskEngine.RiskAssessment riskAssessment = riskEngine.assessRisk(riskInput);
        RiskEngine.Result risk = riskEngine.score(riskInput);

        // ---- assemble reasons ------------------------------------
        List<String> reasons = new ArrayList<>();
        if (multi.flagged()) {
            reasons.add("CRITICAL SECURITY ALARM: Hard Rejection Override — Multiple-Identity Fraud (Face matches stored embedding for a different document number)");
        }
        if (blacklist.matched()) {
            reasons.add("CRITICAL SECURITY ALARM: Hard Rejection Override — Watchlist Blacklist Hit (" + blacklist.reason() + ")");
        }
        if (validation.mrzChecksumFailed()) {
            reasons.add("CRITICAL SECURITY ALARM: Hard Rejection Override — MRZ Checksum Checkdigit Validation Failed");
        }
        reasons.addAll(nullSafe(ai.ocr() == null ? null : ai.ocr().notes()));
        reasons.addAll(nullSafe(ai.tamper() == null ? null : ai.tamper().notes()));
        reasons.addAll(nullSafe(ai.face() == null ? null : ai.face().notes()));
        reasons.addAll(validation.reasons());
        reasons.add(blacklist.reason());
        if (multi.flagged()) reasons.add(multi.detail());
        reasons.addAll(risk.reasons());

        // ---- 10. persist verification result ------------------------
        VerificationResult vr = new VerificationResult();
        vr.setDocumentId(doc.getId());
        vr.setOcrStatus(ai.ocr() != null && Boolean.TRUE.equals(hasFields(ai.ocr())) ? "OK" : "PARTIAL");
        vr.setValidationStatus(validation.status());
        vr.setTamperingScore(round(tamperComposite));
        vr.setPhotoTampering(round(safe(ai.tamper() == null ? null : ai.tamper().photoTampering())));
        vr.setTextTampering(round(safe(ai.tamper() == null ? null : ai.tamper().textTampering())));
        vr.setStampTampering(round(safe(ai.tamper() == null ? null : ai.tamper().stampTampering())));
        vr.setPhotoForgeryStatus(pf != null && pf.status() != null ? pf.status() : "NOT_PERFORMED");
        vr.setPhotoForgeryConfidence(pf != null && pf.confidence() != null ? round(pf.confidence()) : 0.0);
        vr.setPhotoForgeryReasons(pf != null && pf.reasons() != null ? pf.reasons() : List.of());
        vr.setTextManipulationStatus(tm != null && tm.status() != null ? tm.status() : "NOT_PERFORMED");
        vr.setTextManipulationConfidence(tm != null && tm.confidence() != null ? round(tm.confidence()) : 0.0);
        vr.setTextManipulationFields(tm != null && tm.suspiciousFields() != null ? tm.suspiciousFields() : List.of());
        vr.setTextManipulationReasons(tm != null && tm.reasons() != null ? tm.reasons() : List.of());
        vr.setStampForgeryStatus(sf != null && sf.status() != null ? sf.status() : "NOT_PERFORMED");
        vr.setStampForgeryConfidence(sf != null && sf.confidence() != null ? round(sf.confidence()) : 0.0);
        vr.setStampForgeryReasons(sf != null && sf.reasons() != null ? sf.reasons() : List.of());
        vr.setMetadataStatus(ma != null && ma.status() != null ? ma.status() : "NOT_AVAILABLE");
        vr.setMetadataConfidence(ma != null && ma.confidence() != null ? round(ma.confidence()) : 0.0);
        vr.setMetadataReasons(ma != null && ma.reasons() != null ? ma.reasons() : List.of());
        if (validation.vizMrzCrossValidation() != null) {
            vr.setVizMrzStatus(validation.vizMrzCrossValidation().status());
            vr.setVizMrzMatchedFields(validation.vizMrzCrossValidation().matchedFields());
            vr.setVizMrzMismatches(validation.vizMrzCrossValidation().mismatches());
            vr.setVizMrzReasons(validation.vizMrzCrossValidation().reasons());
        }
        if (validation.expiryValidation() != null) {
            vr.setExpiryStatus(validation.expiryValidation().status());
            vr.setExpiryDateValidated(validation.expiryValidation().expiryDate());
            vr.setExpiryDaysRemaining(validation.expiryValidation().daysRemaining());
            vr.setExpirySource(validation.expiryValidation().source());
        }
        vr.setFaceMatchScore(round(faceScore(ai.face())));
        vr.setFaceMatchStatus(faceStatus(ai.face(), faceScore(ai.face())));
        vr.setLivenessStatus(ai.face() == null ? "UNKNOWN" : String.valueOf(ai.face().livenessStatus()));
        vr.setBlacklistStatus(blacklist.matched() ? "HIT" : "CLEAR");
        vr.setRiskScore(riskAssessment.score());
        vr.setRiskLevel(riskAssessment.level());
        vr.setRiskAssessment(riskAssessment);
        vr.setFinalResult(deriveFinalResult(riskAssessment.level(), validation, blacklist, multi));
        vr.setReasons(reasons);
        vr.setVerifiedBy(currentUser.get().getId());
        vr = verificationRepo.save(vr);

        if (ai.tamper() != null && ai.tamper().elaHeatmapBase64() != null) {
            heatmaps.put(vr.getId(), ai.tamper().elaHeatmapBase64());
        }

        // ---- store face embedding for future correlation (only when live face supplied) -----------
        if (facePerformed && ai.face() != null && ai.face().embedding() != null && !ai.face().embedding().isEmpty()) {
            FaceEmbedding fe = new FaceEmbedding();
            fe.setVerificationId(vr.getId());
            fe.setDocumentNumber(doc.getDocumentNumber());
            fe.setEmbedding(ai.face().embedding());
            embeddingRepo.save(fe);
        }

        // ---- 10/11. hash + blockchain write -------------------------
        String recordHash = computeRecordHash(vr);
        String txId = blockchain.registerVerification(String.valueOf(vr.getId()), recordHash);
        auditService.record(vr.getId(), currentUser.get().getId(), "VERIFICATION_CREATED", ip,
                recordHash, txId, "VERIFIED");

        // ---- 13. notification on HIGH risk ---------------------------
        if ("HIGH".equals(risk.level())) {
            notificationService.raise(vr.getId(), "HIGH_RISK_ALERT",
                    currentUser.get().getCheckpointId(),
                    "High-risk verification " + vr.getId() + " — " + vr.getFinalResult());
        }

        return toView(doc, extracted, vr, ai.tamper(), recordHash, txId);
    }

    public VerificationDtos.VerificationView get(Long verificationId) {
        VerificationResult vr = verificationRepo.findById(verificationId)
                .orElseThrow(() -> ApiException.notFound("Verification " + verificationId));
        Document doc = documentService.require(vr.getDocumentId());
        ExtractedData extracted = extractedRepo.findByDocumentId(doc.getId()).orElse(new ExtractedData());
        String hash = computeRecordHash(vr);
        String txId = blockchain.getVerification(String.valueOf(vr.getId()))
                .map(BlockchainService.LedgerRecord::txId).orElse(null);
        return toViewStored(doc, extracted, vr, hash, txId);
    }

    /** re-hash the current DB row and compare against the ledger (Spec step 14). */
    public Map<String, Object> integrityCheck(Long verificationId) {
        VerificationResult vr = verificationRepo.findById(verificationId)
                .orElseThrow(() -> ApiException.notFound("Verification " + verificationId));
        String currentHash = computeRecordHash(vr);
        Optional<BlockchainService.LedgerRecord> ledger = blockchain.getVerification(String.valueOf(vr.getId()));
        boolean intact = ledger.map(r -> r.recordHash().equals(currentHash)).orElse(false);
        return Map.of(
                "verificationId", vr.getId(),
                "currentHash", currentHash,
                "ledgerHash", ledger.map(BlockchainService.LedgerRecord::recordHash).orElse("<none>"),
                "integrityStatus", intact ? "INTACT" : "TAMPERED");
    }

    public List<VerificationDtos.VerificationView> listAll() {
        return verificationRepo.findAll(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "id"))
                .stream()
                .map(vr -> get(vr.getId()))
                .toList();
    }

    public String heatmap(Long verificationId) {
        return heatmaps.get(verificationId);
    }

    public Map<String, Object> getStats() {
        List<VerificationResult> all = verificationRepo.findAll();
        long total = all.size();
        long high = all.stream().filter(v -> "HIGH".equals(v.getRiskLevel())).count();
        long medium = all.stream().filter(v -> "MEDIUM".equals(v.getRiskLevel())).count();
        long low = all.stream().filter(v -> "LOW".equals(v.getRiskLevel())).count();
        long clear = all.stream().filter(v -> "CLEAR".equals(v.getFinalResult())).count();
        long review = all.stream().filter(v -> "MANUAL_REVIEW".equals(v.getFinalResult())).count();
        long reject = all.stream().filter(v -> "REJECT".equals(v.getFinalResult())).count();
        long blacklist = all.stream().filter(v -> "HIT".equals(v.getBlacklistStatus())).count();
        double avgTamper = all.stream().mapToDouble(v -> v.getTamperingScore() != null ? v.getTamperingScore() : 0.0).average().orElse(0.0);

        return Map.of(
                "totalScreened", total,
                "highRiskCount", high,
                "mediumRiskCount", medium,
                "lowRiskCount", low,
                "clearCount", clear,
                "manualReviewCount", review,
                "rejectCount", reject,
                "blacklistHits", blacklist,
                "avgTamperScore", Math.round(avgTamper * 100.0) / 100.0
        );
    }

    // ================= helpers =================

    private ExtractedData buildExtracted(Document doc, AiDtos.OcrResult ocr) {
        ExtractedData e = extractedRepo.findByDocumentId(doc.getId()).orElseGet(ExtractedData::new);
        e.setDocumentId(doc.getId());
        Map<String, String> f = ocr != null && ocr.fields() != null ? ocr.fields() : Map.of();

        String name = blankToNull(f.get("name"));
        String passportNum = blankToNull(f.getOrDefault("passportNumber", f.get("documentNumber")));
        if (passportNum == null) {
            passportNum = blankToNull(doc.getDocumentNumber());
        }

        e.setName(name);
        e.setPassportNumber(passportNum);
        e.setNationality(blankToNull(f.get("nationality")));
        e.setDateOfBirth(parseDate(f.get("dateOfBirth")));
        e.setGender(blankToNull(f.get("gender")));
        e.setIssueDate(parseDate(f.get("issueDate")));
        e.setExpiryDate(parseDate(f.get("expiryDate")));

        String mrz = ocr != null ? blankToNull(ocr.mrz()) : null;
        e.setMrzData(mrz);
        e.setVisualZone(ocr != null && ocr.visualZone() != null ? ocr.visualZone() : Map.of());
        e.setOcrConfidence(ocr != null ? ocr.confidence() : null);
        return e;
    }

    private record MultiIdentity(boolean flagged, String detail, String matchedDocNumber, double similarity) {}

    private MultiIdentity checkMultiIdentity(AiDtos.FaceResult face, ExtractedData currentExtracted, Long currentDocId) {
        if (face == null || face.embedding() == null || face.embedding().isEmpty()) {
            return new MultiIdentity(false, "NO_EMBEDDING", null, 0.0);
        }

        String currentDocNum = currentExtracted != null ? currentExtracted.getPassportNumber() : null;
        String currentName = currentExtracted != null ? normalizeName(currentExtracted.getName()) : null;
        LocalDate currentDob = currentExtracted != null ? currentExtracted.getDateOfBirth() : null;
        String normCurrentDocNum = normalizeDocNum(currentDocNum);

        double threshold = 0.62; // ArcFace cosine similarity decision threshold

        for (FaceEmbedding stored : embeddingRepo.findAll()) {
            boolean skipCurrentDocument = false;
            // Skip embeddings belonging to the current document run
            if (stored.getVerificationId() != null) {
                Optional<VerificationResult> storedVr = verificationRepo.findById(stored.getVerificationId());
                if (storedVr.isPresent() && currentDocId != null && currentDocId.equals(storedVr.get().getDocumentId())) {
                    skipCurrentDocument = true;
                    continue;
                }
            }

            String normStoredDocNum = normalizeDocNum(stored.getDocumentNumber());
            boolean skipSameDocumentNumber = false;
            // Skip exact document number matches (re-scan of the same document)
            if (normCurrentDocNum != null && normStoredDocNum != null && normCurrentDocNum.equalsIgnoreCase(normStoredDocNum)) {
                skipSameDocumentNumber = true;
                continue;
            }

            double sim = FaceMath.cosineSimilarity(face.embedding(), stored.getEmbedding());
            if (sim >= threshold) {
                // Identity correlation audit: Check if stored record belongs to the SAME person vs a DIFFERENT identity
                boolean samePerson = false;
                boolean sameName = false;
                boolean dobConflict = false;
                String storedName = null;
                LocalDate storedDob = null;
                Long storedDocId = null;

                if (stored.getVerificationId() != null) {
                    Optional<VerificationResult> storedVr = verificationRepo.findById(stored.getVerificationId());
                    if (storedVr.isPresent()) {
                        storedDocId = storedVr.get().getDocumentId();
                        Optional<ExtractedData> storedExt = extractedRepo.findByDocumentId(storedDocId);
                        if (storedExt.isPresent()) {
                            ExtractedData ext = storedExt.get();
                            storedName = normalizeName(ext.getName());
                            storedDob = ext.getDateOfBirth();

                            sameName = currentName != null && storedName != null && isSameName(currentName, storedName);
                            dobConflict = currentDob != null && storedDob != null && !currentDob.equals(storedDob);

                            // Strict identity matching: Same person iff names match AND DOBs do not conflict
                            if (sameName && !dobConflict) {
                                samePerson = true;
                            }
                        }
                    }
                }

                log.info("[MultiIdentityAudit] curDocId={} curDocNum={} curName={} curDob={} | storedVrId={} storedDocId={} storedDocNum={} storedName={} storedDob={} | sim={:.4f} sameName={} dobConflict={} samePerson={}",
                        currentDocId, currentDocNum, currentName, currentDob, stored.getVerificationId(), storedDocId, stored.getDocumentNumber(), storedName, storedDob, sim, sameName, dobConflict, samePerson);

                if (!samePerson) {
                    String matchedDoc = stored.getDocumentNumber() != null ? stored.getDocumentNumber() : "ID#" + stored.getVerificationId();
                    return new MultiIdentity(true, String.format(
                            "CRITICAL SECURITY ALARM: Hard Rejection Override — Multiple-Identity Fraud (Face matches stored embedding for document %s, cosine %.2f)",
                            matchedDoc, sim), matchedDoc, sim);
                }
            }
        }
        return new MultiIdentity(false, "CLEAR", null, 0.0);
    }

    private static String normalizeName(String name) {
        if (name == null) return null;
        String s = name.trim().toUpperCase().replaceAll("[^A-Z ]", "").replaceAll("\\s+", " ");
        return s.isBlank() ? null : s;
    }

    private static boolean isSameName(String n1, String n2) {
        if (n1 == null || n2 == null) return false;
        if (n1.equalsIgnoreCase(n2)) return true;
        String[] parts1 = n1.split(" ");
        String[] parts2 = n2.split(" ");
        if (parts1.length >= 2 && parts2.length >= 2) {
            if (parts1[0].equalsIgnoreCase(parts2[0]) && parts1[parts1.length - 1].equalsIgnoreCase(parts2[parts2.length - 1])) {
                return true;
            }
        }
        return false;
    }

    private static String normalizeDocNum(String docNum) {
        if (docNum == null) return null;
        String s = docNum.trim().toUpperCase().replaceAll("[^A-Z0-9]", "");
        if (s.isEmpty() || s.equals("UNKNOWN") || s.equals("APELLIDOS") || s.equals("STAATER") || s.equals("NONE") || s.length() < 3) {
            return null;
        }
        return s;
    }


    private double compositeTamper(AiDtos.TamperResult t) {
        if (t == null) return 0.0;
        double comp = safe(t.tamperingScore());
        double max = Math.max(safe(t.photoTampering()), Math.max(safe(t.textTampering()), safe(t.stampTampering())));
        return Math.max(comp, max);
    }

    private double faceScore(AiDtos.FaceResult f) {
        return f == null ? 0.0 : safe(f.faceMatchScore());
    }

    private String faceStatus(AiDtos.FaceResult f, double score) {
        if (f == null || f.faceMatchStatus() == null) return "NOT_PERFORMED";
        String status = f.faceMatchStatus().toUpperCase();
        if (status.equals("SKIPPED") || status.equals("NOT_PERFORMED") || status.equals("UNKNOWN")) {
            return "NOT_PERFORMED";
        }
        return score >= props.risk().thresholds().faceMatch() ? "MATCH" : "MISMATCH";
    }

    private String deriveFinalResult(String riskLevel, ValidationEngine.Outcome v,
                                     BlacklistService.Hit b, MultiIdentity m) {
        if (b.matched() || v.mrzChecksumFailed()) return "REJECT";
        if ("HIGH".equals(riskLevel)) return "REJECT";
        if ("MEDIUM".equals(riskLevel) || v.expired() || m.flagged()) return "MANUAL_REVIEW";
        return "CLEAR";
    }

    private String computeRecordHash(VerificationResult vr) {
        try {
            String canonical = objectMapper.writeValueAsString(Map.of(
                    "documentId", vr.getDocumentId(),
                    "validationStatus", str(vr.getValidationStatus()),
                    "tamperingScore", str(vr.getTamperingScore()),
                    "faceMatchScore", str(vr.getFaceMatchScore()),
                    "blacklistStatus", str(vr.getBlacklistStatus()),
                    "riskScore", str(vr.getRiskScore()),
                    "riskLevel", str(vr.getRiskLevel()),
                    "finalResult", str(vr.getFinalResult())));
            return HashUtil.sha256(canonical);
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }

    private VerificationDtos.VerificationView toView(Document doc, ExtractedData e, VerificationResult vr,
                                                    AiDtos.TamperResult t, String hash, String txId) {
        boolean overrideTriggered = false;
        String overrideReason = null;
        String multiStatus = "CLEAR";
        String multiDetail = "No duplicate identity match detected in historical database";

        if (vr.getReasons() != null) {
            for (String r : vr.getReasons()) {
                if (r != null && r.contains("Hard Rejection Override")) {
                    overrideTriggered = true;
                    overrideReason = r;
                }
                if (r != null && (r.contains("Multiple-Identity") || r.contains("Multiple-identity"))) {
                    multiStatus = "POTENTIAL_MATCH_DETECTED";
                    multiDetail = r;
                }
            }
        }
        if (!overrideTriggered && "REJECT".equals(vr.getFinalResult()) && ("LOW".equals(vr.getRiskLevel()) || "MEDIUM".equals(vr.getRiskLevel()))) {
            overrideTriggered = true;
            overrideReason = "HARD SECURITY RULE OVERRIDE: Security rule triggered hard rejection independently of numerical risk score";
        }

        VerificationDtos.VizMrzCrossValidationView vizMrzView = null;
        if (vr.getVizMrzStatus() != null) {
            List<VerificationDtos.VizMrzCrossValidationView.FieldMismatchView> mismatchesView = List.of();
            if (vr.getVizMrzMismatches() != null) {
                mismatchesView = vr.getVizMrzMismatches().stream()
                        .map(m -> new VerificationDtos.VizMrzCrossValidationView.FieldMismatchView(m.field(), m.vizValue(), m.mrzValue()))
                        .toList();
            }
            vizMrzView = new VerificationDtos.VizMrzCrossValidationView(
                    vr.getVizMrzStatus(),
                    vr.getVizMrzMatchedFields() != null ? vr.getVizMrzMatchedFields() : List.of(),
                    mismatchesView,
                    vr.getVizMrzReasons() != null ? vr.getVizMrzReasons() : List.of()
            );
        }

        VerificationDtos.ExpiryValidationView expiryView = null;
        if (vr.getExpiryStatus() != null) {
            expiryView = new VerificationDtos.ExpiryValidationView(
                    vr.getExpiryStatus(),
                    vr.getExpiryDateValidated() != null ? vr.getExpiryDateValidated().toString() : null,
                    vr.getExpiryDaysRemaining(),
                    vr.getExpirySource()
            );
        }

        VerificationDtos.RiskAssessmentView riskAssessmentView = null;
        if (vr.getRiskAssessment() != null) {
            var ra = vr.getRiskAssessment();
            List<VerificationDtos.RiskComponentView> comps = ra.components() != null ? ra.components().stream()
                    .map(c -> new VerificationDtos.RiskComponentView(c.code(), c.label(), c.points(), c.triggered(), c.reason()))
                    .toList() : List.of();
            List<VerificationDtos.RiskComponentView> trigComps = ra.triggeredComponents() != null ? ra.triggeredComponents().stream()
                    .map(c -> new VerificationDtos.RiskComponentView(c.code(), c.label(), c.points(), c.triggered(), c.reason()))
                    .toList() : List.of();
            riskAssessmentView = new VerificationDtos.RiskAssessmentView(
                    ra.score(), ra.level(), comps, trigComps, ra.decision(), ra.decisionBasis(), ra.summary(), ra.securityOverrideTriggered(), ra.securityOverrideReason()
            );
        }

        VerificationDtos.MetadataAnalysisView metadataView = null;
        AiDtos.MetadataAnalysisResult ma = t != null ? t.metadataAnalysis() : null;
        if (ma != null) {
            metadataView = new VerificationDtos.MetadataAnalysisView(
                    ma.status() != null ? ma.status() : "NOT_AVAILABLE",
                    ma.confidence() != null ? ma.confidence() : 0.95,
                    ma.signals() != null ? ma.signals() : List.of(),
                    ma.metadata() != null ? ma.metadata() : Map.of(),
                    ma.reasons() != null ? ma.reasons() : List.of()
            );
        } else if (vr.getMetadataStatus() != null) {
            metadataView = new VerificationDtos.MetadataAnalysisView(
                    vr.getMetadataStatus(),
                    vr.getMetadataConfidence() != null ? vr.getMetadataConfidence() : 0.95,
                    List.of(),
                    Map.of(),
                    vr.getMetadataReasons() != null ? vr.getMetadataReasons() : List.of()
            );
        }

        return new VerificationDtos.VerificationView(
                vr.getId(), doc.getId(), doc.getDocumentType(),
                extractedView(e),
                vr.getOcrStatus(), vr.getValidationStatus(),
                vr.getTamperingScore(), vr.getPhotoTampering(), vr.getTextTampering(), vr.getStampTampering(),
                vr.getPhotoForgeryStatus(), vr.getPhotoForgeryConfidence(), vr.getPhotoForgeryReasons(),
                vr.getTextManipulationStatus(), vr.getTextManipulationConfidence(), vr.getTextManipulationFields(), vr.getTextManipulationReasons(),
                vr.getStampForgeryStatus(), vr.getStampForgeryConfidence(), vr.getStampForgeryReasons(),
                vr.getMetadataStatus(), vr.getMetadataConfidence(), vr.getMetadataReasons(), metadataView,
                vizMrzView,
                expiryView,
                riskAssessmentView,
                t != null ? t.elaHeatmapBase64() : heatmaps.get(vr.getId()),
                vr.getFaceMatchScore(), vr.getFaceMatchStatus(), vr.getLivenessStatus(),
                vr.getBlacklistStatus(), multiStatus, multiDetail,
                vr.getRiskScore(), vr.getRiskLevel(), vr.getFinalResult(),
                overrideTriggered, overrideReason,
                vr.getReasons(), hash, txId, vr.getCreatedAt());
    }

    private VerificationDtos.VerificationView toViewStored(Document doc, ExtractedData e, VerificationResult vr,
                                                          String hash, String txId) {
        return toView(doc, e, vr, null, hash, txId);
    }

    @SuppressWarnings("unchecked")
    private VerificationDtos.ExtractedView extractedView(ExtractedData e) {
        Map<String, Object> vz = e.getVisualZone() != null ? e.getVisualZone() : Map.of();
        String cat = vz.get("documentCategory") != null ? String.valueOf(vz.get("documentCategory")) : "NATIONAL_ID";
        String sub = vz.get("documentSubtype") != null ? String.valueOf(vz.get("documentSubtype"))
                : (vz.get("detectedDocumentType") != null ? String.valueOf(vz.get("detectedDocumentType")) : "NATIONAL_ID_CARD");
        List<String> fields = vz.get("applicableFields") instanceof List ? (List<String>) vz.get("applicableFields") : List.of();
        List<String> checks = vz.get("applicableChecks") instanceof List ? (List<String>) vz.get("applicableChecks") : List.of();

        return new VerificationDtos.ExtractedView(
                e.getName(), e.getPassportNumber(), e.getNationality(),
                str(e.getDateOfBirth()), e.getGender(), str(e.getIssueDate()), str(e.getExpiryDate()),
                e.getMrzData(), e.getOcrConfidence(), e.getVisualZone(),
                cat, sub, fields, checks);
    }

    private static List<String> nullSafe(List<String> l) { return l == null ? List.of() : l; }
    private static double safe(Double d) { return d == null ? 0.0 : d; }
    private static Double round(double d) { return Math.round(d * 10000.0) / 10000.0; }
    private static String str(Object o) { return o == null ? null : o.toString(); }

    private static final DateTimeFormatter[] DATE_FORMATS = {
            DateTimeFormatter.ISO_LOCAL_DATE,
            DateTimeFormatter.ofPattern("dd/MM/yyyy"),
            DateTimeFormatter.ofPattern("MM/dd/yyyy"),
            DateTimeFormatter.ofPattern("dd-MM-yyyy"),
            DateTimeFormatter.ofPattern("dd MMM yyyy", Locale.ENGLISH),
            DateTimeFormatter.ofPattern("dd MMMM yyyy", Locale.ENGLISH),
    };

    private static LocalDate parseDate(String s) {
        if (s == null || s.isBlank()) return null;
        String trimmed = s.trim();
        for (DateTimeFormatter fmt : DATE_FORMATS) {
            try {
                return LocalDate.parse(trimmed, fmt);
            } catch (DateTimeParseException ignored) {
                // try next format
            }
        }
        return null;
    }

    private static String blankToNull(String s) {
        return s == null || s.isBlank() ? null : s.trim();
    }

    private static Boolean hasFields(AiDtos.OcrResult ocr) {
        return ocr.fields() != null && !ocr.fields().isEmpty();
    }
}
