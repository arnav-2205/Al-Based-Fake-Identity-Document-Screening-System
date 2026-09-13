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
        }
        if (ai.ocr() != null && ai.ocr().visualZone() != null && ai.ocr().visualZone().get("detectedDocumentType") != null) {
            String detectedType = String.valueOf(ai.ocr().visualZone().get("detectedDocumentType"));
            if (!"UNKNOWN".equalsIgnoreCase(detectedType) && ("PASSPORT".equalsIgnoreCase(doc.getDocumentType()) || "NATIONAL_ID".equalsIgnoreCase(doc.getDocumentType()))) {
                doc.setDocumentType(detectedType);
            }
        }

        // ---- 6. deterministic validation -----------------------------
        ValidationEngine.Outcome validation = validationEngine.validate(extracted, ai.ocr());

        // ---- 7. blacklist lookup ------------------------------------
        BlacklistService.Hit blacklist = blacklistService.check(
                extracted.getPassportNumber(), extracted.getName(), extracted.getDateOfBirth());

        // ---- 8. multi-identity check --------------------------------
        MultiIdentity multi = checkMultiIdentity(ai.face(), doc.getDocumentNumber());

        // ---- tamper composite ------------------------------------
        double tamperComposite = compositeTamper(ai.tamper());

        boolean facePerformed = liveFaceImage != null
                && ai.face() != null && ai.face().faceMatchScore() != null
                && !"UNKNOWN".equalsIgnoreCase(String.valueOf(ai.face().faceMatchStatus()));
        boolean livenessFailed = ai.face() != null && "SPOOF".equalsIgnoreCase(String.valueOf(ai.face().livenessStatus()));

        // ---- 9. risk scoring -----------------------------------
        RiskEngine.Result risk = riskEngine.score(new RiskEngine.Input(
                tamperComposite,
                faceScore(ai.face()),
                validation.failed(),
                blacklist.matched(),
                multi.flagged(),
                livenessFailed,
                facePerformed));

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
        vr.setFaceMatchScore(round(faceScore(ai.face())));
        vr.setFaceMatchStatus(faceStatus(ai.face(), faceScore(ai.face())));
        vr.setLivenessStatus(ai.face() == null ? "UNKNOWN" : String.valueOf(ai.face().livenessStatus()));
        vr.setBlacklistStatus(blacklist.matched() ? "HIT" : "CLEAR");
        vr.setRiskScore(risk.score());
        vr.setRiskLevel(risk.level());
        vr.setFinalResult(deriveFinalResult(risk.level(), validation, blacklist, multi));
        vr.setReasons(reasons);
        vr.setVerifiedBy(currentUser.get().getId());
        vr = verificationRepo.save(vr);

        if (ai.tamper() != null && ai.tamper().elaHeatmapBase64() != null) {
            heatmaps.put(vr.getId(), ai.tamper().elaHeatmapBase64());
        }

        // ---- store face embedding for future correlation -----------
        if (ai.face() != null && ai.face().embedding() != null && !ai.face().embedding().isEmpty()) {
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

    private MultiIdentity checkMultiIdentity(AiDtos.FaceResult face, String currentDocNumber) {
        if (face == null || face.embedding() == null || face.embedding().isEmpty()) {
            return new MultiIdentity(false, "NO_EMBEDDING", null, 0.0);
        }
        String normCurrent = normalizeDocNum(currentDocNumber);
        double threshold = 0.62; // ArcFace cosine similarity threshold
        for (FaceEmbedding stored : embeddingRepo.findAll()) {
            String normStored = normalizeDocNum(stored.getDocumentNumber());
            // Ignore missing/unparsed document numbers or re-scans of the EXACT same document number
            if (normStored == null || (normCurrent != null && normStored.equalsIgnoreCase(normCurrent))) {
                continue;
            }
            double sim = FaceMath.cosineSimilarity(face.embedding(), stored.getEmbedding());
            if (sim >= threshold) {
                return new MultiIdentity(true, String.format(
                        "Potential Multiple-Identity Match: Face matches stored embedding for document %s (cosine %.2f)",
                        stored.getDocumentNumber(), sim), stored.getDocumentNumber(), sim);
            }
        }
        return new MultiIdentity(false, "CLEAR", null, 0.0);
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

        return new VerificationDtos.VerificationView(
                vr.getId(), doc.getId(), doc.getDocumentType(),
                extractedView(e),
                vr.getOcrStatus(), vr.getValidationStatus(),
                vr.getTamperingScore(), vr.getPhotoTampering(), vr.getTextTampering(), vr.getStampTampering(),
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
