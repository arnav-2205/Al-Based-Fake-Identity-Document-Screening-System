package gov.mha.screening.risk;

import gov.mha.screening.config.AppProperties;
import gov.mha.screening.validation.ExpiryValidation;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

/**
 * Weighted, rule-based, explainable risk scoring (Spec Part 6).
 * No ML — deterministic and defensible.
 *
 * risk_score = w1*tamper + w2*(1-face) + w3*validationFailed
 *            + w4*blacklistHit + w5*multiIdentity + w6*livenessFailed
 *            + photoForgery + textManipulation + vizMrzMismatch
 * scaled to 0..100.
 */
@Service
@RequiredArgsConstructor
public class RiskEngine {

    private final AppProperties props;

    public record Input(
            double tamperingScore,        // 0..1 (max of photo/text/stamp or composite)
            double faceMatchScore,        // 0..1
            boolean validationFailed,
            boolean blacklistHit,
            boolean multipleIdentityFlag,
            boolean livenessFailed,
            boolean faceCheckPerformed,
            boolean photoForgerySuspicious,
            boolean textManipulationSuspicious,
            boolean vizMrzMismatch,
            ExpiryValidation expiryValidation,
            boolean stampForgerySuspicious,
            boolean metadataSuspicious
    ) {
        public Input(double tamperingScore, double faceMatchScore, boolean validationFailed,
                     boolean blacklistHit, boolean multipleIdentityFlag, boolean livenessFailed,
                     boolean faceCheckPerformed) {
            this(tamperingScore, faceMatchScore, validationFailed, blacklistHit, multipleIdentityFlag,
                 livenessFailed, faceCheckPerformed, false, false, false, null, false, false);
        }

        public Input(double tamperingScore, double faceMatchScore, boolean validationFailed,
                     boolean blacklistHit, boolean multipleIdentityFlag, boolean livenessFailed,
                     boolean faceCheckPerformed, boolean photoForgerySuspicious) {
            this(tamperingScore, faceMatchScore, validationFailed, blacklistHit, multipleIdentityFlag,
                 livenessFailed, faceCheckPerformed, photoForgerySuspicious, false, false, null, false, false);
        }

        public Input(double tamperingScore, double faceMatchScore, boolean validationFailed,
                     boolean blacklistHit, boolean multipleIdentityFlag, boolean livenessFailed,
                     boolean faceCheckPerformed, boolean photoForgerySuspicious, boolean textManipulationSuspicious) {
            this(tamperingScore, faceMatchScore, validationFailed, blacklistHit, multipleIdentityFlag,
                 livenessFailed, faceCheckPerformed, photoForgerySuspicious, textManipulationSuspicious, false, null, false, false);
        }

        public Input(double tamperingScore, double faceMatchScore, boolean validationFailed,
                     boolean blacklistHit, boolean multipleIdentityFlag, boolean livenessFailed,
                     boolean faceCheckPerformed, boolean photoForgerySuspicious, boolean textManipulationSuspicious,
                     boolean vizMrzMismatch) {
            this(tamperingScore, faceMatchScore, validationFailed, blacklistHit, multipleIdentityFlag,
                 livenessFailed, faceCheckPerformed, photoForgerySuspicious, textManipulationSuspicious, vizMrzMismatch, null, false, false);
        }

        public Input(double tamperingScore, double faceMatchScore, boolean validationFailed,
                     boolean blacklistHit, boolean multipleIdentityFlag, boolean livenessFailed,
                     boolean faceCheckPerformed, boolean photoForgerySuspicious, boolean textManipulationSuspicious,
                     boolean vizMrzMismatch, ExpiryValidation expiryValidation) {
            this(tamperingScore, faceMatchScore, validationFailed, blacklistHit, multipleIdentityFlag,
                 livenessFailed, faceCheckPerformed, photoForgerySuspicious, textManipulationSuspicious, vizMrzMismatch, expiryValidation, false, false);
        }

        public Input(double tamperingScore, double faceMatchScore, boolean validationFailed,
                     boolean blacklistHit, boolean multipleIdentityFlag, boolean livenessFailed,
                     boolean faceCheckPerformed, boolean photoForgerySuspicious, boolean textManipulationSuspicious,
                     boolean vizMrzMismatch, ExpiryValidation expiryValidation, boolean stampForgerySuspicious) {
            this(tamperingScore, faceMatchScore, validationFailed, blacklistHit, multipleIdentityFlag,
                 livenessFailed, faceCheckPerformed, photoForgerySuspicious, textManipulationSuspicious, vizMrzMismatch, expiryValidation, stampForgerySuspicious, false);
        }
    }

    public record RiskComponent(
            String code,
            String label,
            double points,
            boolean triggered,
            String reason
    ) {}

    public record RiskAssessment(
            double score,
            String level,
            List<RiskComponent> components,
            List<RiskComponent> triggeredComponents,
            String decision,
            List<String> decisionBasis,
            String summary,
            boolean securityOverrideTriggered,
            String securityOverrideReason
    ) {}

    public record Result(double score, String level, List<String> reasons) {}

    public RiskAssessment assessRisk(Input in) {
        var w = props.risk().weights();
        List<RiskComponent> components = new ArrayList<>();

        // 1. Document Tampering
        boolean tamperTrig = in.tamperingScore() > props.risk().thresholds().tamperFlag();
        double tamperPts = tamperTrig ? round2(w.tampering() * clamp(in.tamperingScore())) : 0.0;
        components.add(new RiskComponent(
                "TAMPERING",
                "Document Tampering",
                tamperPts,
                tamperTrig,
                tamperTrig ? String.format("Document tampering score %.2f detected (+%.1f pts)", in.tamperingScore(), tamperPts)
                           : "No document image tampering detected (+0.0 pts)"
        ));

        // 2. Face Verification Mismatch
        boolean faceTrig = in.faceCheckPerformed() && in.faceMatchScore() < props.risk().thresholds().faceMatch();
        double facePts = faceTrig ? round2(w.face() * clamp(1.0 - in.faceMatchScore())) : 0.0;
        components.add(new RiskComponent(
                "FACE_MISMATCH",
                "Face Verification",
                facePts,
                faceTrig,
                in.faceCheckPerformed()
                        ? (faceTrig ? String.format("Live face match %.2f below threshold %.2f (+%.1f pts)", in.faceMatchScore(), props.risk().thresholds().faceMatch(), facePts)
                                    : String.format("Live face matches document photo (%.2f) (+0.0 pts)", in.faceMatchScore()))
                        : "Face check not performed (no live photo supplied) (+0.0 pts)"
        ));

        // 3. Deterministic Validation Failure
        double valPts = in.validationFailed() ? (double) w.validation() : 0.0;
        boolean valTrig = in.validationFailed();
        components.add(new RiskComponent(
                "VALIDATION_FAILURE",
                "Deterministic Validation",
                valPts,
                valTrig,
                valTrig ? String.format("Deterministic validation failed (MRZ checksum or structural error) (+%.1f pts)", valPts)
                        : "Deterministic validation checks passed (+0.0 pts)"
        ));

        // 4. Watchlist / Blacklist
        double blackPts = in.blacklistHit() ? (double) w.blacklist() : 0.0;
        boolean blackTrig = in.blacklistHit();
        components.add(new RiskComponent(
                "WATCHLIST_HIT",
                "Watchlist / Blacklist",
                blackPts,
                blackTrig,
                blackTrig ? String.format("Watchlist blacklist match detected (+%.1f pts)", blackPts)
                          : "No watchlist match found (+0.0 pts)"
        ));

        // 5. Multiple-Identity Fraud
        double multiPts = in.multipleIdentityFlag() ? (double) w.multiIdentity() : 0.0;
        boolean multiTrig = in.multipleIdentityFlag();
        components.add(new RiskComponent(
                "MULTI_IDENTITY",
                "Multiple-Identity Fraud",
                multiPts,
                multiTrig,
                multiTrig ? String.format("Face matches stored embedding for a different document (+%.1f pts)", multiPts)
                          : "No duplicate identity match detected (+0.0 pts)"
        ));

        // 6. Liveness Failure
        double livePts = in.livenessFailed() ? (double) w.liveness() : 0.0;
        boolean liveTrig = in.livenessFailed();
        components.add(new RiskComponent(
                "LIVENESS_FAILURE",
                "Liveness Detection",
                livePts,
                liveTrig,
                liveTrig ? String.format("Live face photo failed liveness check (SPOOF) (+%.1f pts)", livePts)
                         : "Liveness check passed / not performed (+0.0 pts)"
        ));

        // 7. Photo Replacement Forensic Detection
        double photoPts = in.photoForgerySuspicious() ? 15.0 : 0.0;
        boolean photoTrig = in.photoForgerySuspicious();
        components.add(new RiskComponent(
                "PHOTO_REPLACEMENT",
                "Photo Replacement Detection",
                photoPts,
                photoTrig,
                photoTrig ? "Portrait manipulation / photo seam anomaly detected (+15.0 pts)"
                          : "No photo replacement anomalies detected (+0.0 pts)"
        ));

        // 8. Text Manipulation Forensic Detection
        double textPts = in.textManipulationSuspicious() ? 15.0 : 0.0;
        boolean textTrig = in.textManipulationSuspicious();
        components.add(new RiskComponent(
                "TEXT_MANIPULATION",
                "Text Manipulation Detection",
                textPts,
                textTrig,
                textTrig ? "Digital text field modification / overlay patch detected (+15.0 pts)"
                         : "No text field manipulation detected (+0.0 pts)"
        ));

        // 9. VIZ ↔ MRZ Cross-Validation
        double vizPts = in.vizMrzMismatch() ? 15.0 : 0.0;
        boolean vizTrig = in.vizMrzMismatch();
        components.add(new RiskComponent(
                "VIZ_MRZ_MISMATCH",
                "VIZ ↔ MRZ Cross-Validation",
                vizPts,
                vizTrig,
                vizTrig ? "Visual Inspection Zone fields disagree with MRZ data (+15.0 pts)"
                        : "VIZ and MRZ fields match / not applicable (+0.0 pts)"
        ));

        // 10. Document Expiry Validation
        ExpiryValidation exp = in.expiryValidation();
        boolean expiredTrig = exp != null && "EXPIRED".equalsIgnoreCase(exp.status());
        double expPts = expiredTrig ? 15.0 : 0.0;
        String expReason;
        if (expiredTrig) {
            expReason = String.format("Document expired on %s (+15.0 pts)", exp.expiryDate());
        } else if (exp != null && "VALID".equalsIgnoreCase(exp.status())) {
            expReason = String.format("Document valid until %s (+0.0 pts)", exp.expiryDate());
        } else {
            expReason = "Document expiry valid / not applicable (+0.0 pts)";
        }
        components.add(new RiskComponent(
                "EXPIRED_DOCUMENT",
                "Document Expiry",
                expPts,
                expiredTrig,
                expReason
        ));

        // 11. Stamp Forgery Forensic Detection
        double stampPts = in.stampForgerySuspicious() ? 15.0 : 0.0;
        boolean stampTrig = in.stampForgerySuspicious();
        components.add(new RiskComponent(
                "STAMP_FORGERY",
                "Stamp Forgery Detection",
                stampPts,
                stampTrig,
                stampTrig ? "Forged or manipulated document/visa stamp detected (+15.0 pts)"
                          : "No stamp forgery detected (+0.0 pts)"
        ));

        // 12. Image Metadata Anomaly Forensic Detection
        double metaPts = in.metadataSuspicious() ? 5.0 : 0.0;
        boolean metaTrig = in.metadataSuspicious();
        components.add(new RiskComponent(
                "METADATA_ANOMALY",
                "Image Metadata Analysis",
                metaPts,
                metaTrig,
                metaTrig ? "Suspicious image metadata anomalies / editing software traces detected (+5.0 pts)"
                         : "Standard image metadata / metadata not available (+0.0 pts)"
        ));

        // Filter triggered components
        List<RiskComponent> triggered = components.stream().filter(RiskComponent::triggered).toList();

        // Calculate sum of triggered component points
        double rawScore = components.stream().mapToDouble(RiskComponent::points).sum();
        double scaled = round2(Math.min(100.0, rawScore));
        String level = scaled <= 30.0 ? "LOW" : (scaled <= 65.0 ? "MEDIUM" : "HIGH");

        // Decision Basis & Hard Override Detection
        List<String> decisionBasis = new ArrayList<>();
        boolean overrideTriggered = false;
        String overrideReason = null;
        String decision;

        if (in.blacklistHit()) {
            decision = "REJECT";
            overrideTriggered = true;
            overrideReason = "Watchlist Blacklist Hit";
            decisionBasis.add("Security override: Watchlist Blacklist Hit");
        } else if (in.validationFailed()) {
            decision = "REJECT";
            overrideTriggered = true;
            overrideReason = "MRZ Checksum Checkdigit Validation Failed";
            decisionBasis.add("Security override: MRZ Checksum Checkdigit Validation Failed");
        } else if ("HIGH".equals(level)) {
            decision = "REJECT";
            decisionBasis.add(String.format("Risk score (%.1f) exceeded rejection threshold (65.0)", scaled));
        } else if (in.multipleIdentityFlag()) {
            decision = "MANUAL_REVIEW";
            overrideTriggered = true;
            overrideReason = "Multiple-Identity Fraud Detected";
            decisionBasis.add("Security override: Multiple-Identity Fraud (Face matches stored embedding for a different document)");
        } else if (expiredTrig) {
            decision = "MANUAL_REVIEW";
            decisionBasis.add("Document expiry date has passed");
        } else if ("MEDIUM".equals(level)) {
            decision = "MANUAL_REVIEW";
            decisionBasis.add(String.format("Risk score (%.1f) reached manual review threshold (30.0)", scaled));
        } else {
            decision = "CLEAR";
            decisionBasis.add(String.format("Low risk score (%.1f) within clear threshold (30.0)", scaled));
        }

        String summary = String.format("%s risk verification (score %.1f/100) — Final Decision: %s", level, scaled, decision);

        return new RiskAssessment(
                scaled,
                level,
                components,
                triggered,
                decision,
                decisionBasis,
                summary,
                overrideTriggered,
                overrideReason
        );
    }

    public Result score(Input in) {
        RiskAssessment ra = assessRisk(in);
        List<String> reasons = new ArrayList<>();
        for (RiskComponent c : ra.components()) {
            if (c.triggered()) {
                reasons.add(c.reason());
            }
        }
        reasons.addAll(ra.decisionBasis());
        reasons.add(String.format("Final risk score %.1f/100 → %s", ra.score(), ra.level()));
        return new Result(ra.score(), ra.level(), reasons);
    }

    private static double clamp(double v) { return Math.max(0.0, Math.min(1.0, v)); }
    private static double round2(double v) { return Math.round(v * 100.0) / 100.0; }
}
