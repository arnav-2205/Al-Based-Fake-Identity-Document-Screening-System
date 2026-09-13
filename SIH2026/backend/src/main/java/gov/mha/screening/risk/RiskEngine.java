package gov.mha.screening.risk;

import gov.mha.screening.config.AppProperties;
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
            boolean faceCheckPerformed
    ) {}

    public record Result(double score, String level, List<String> reasons) {}

    public Result score(Input in) {
        var w = props.risk().weights();
        List<String> reasons = new ArrayList<>();

        double tamperComponent = w.tampering() * clamp(in.tamperingScore());
        double faceComponent = in.faceCheckPerformed() ? w.face() * clamp(1.0 - in.faceMatchScore()) : 0.0;
        double validationComponent = in.validationFailed() ? w.validation() : 0.0;
        double blacklistComponent = in.blacklistHit() ? w.blacklist() : 0.0;
        double multiIdComponent = in.multipleIdentityFlag() ? w.multiIdentity() : 0.0;
        double livenessComponent = in.livenessFailed() ? w.liveness() : 0.0;

        double raw = tamperComponent + faceComponent + validationComponent
                + blacklistComponent + multiIdComponent + livenessComponent;

        double maxPossible = w.tampering() + w.face() + w.validation()
                + w.blacklist() + w.multiIdentity() + w.liveness();
        double scaled = round2(raw / maxPossible * 100.0);

        reasons.add(String.format("Tamper score %.2f → +%.1f", in.tamperingScore(), tamperComponent));
        if (in.faceCheckPerformed()) {
            reasons.add(String.format("Face match %.2f (threshold %.2f) → +%.1f",
                    in.faceMatchScore(), props.risk().thresholds().faceMatch(), faceComponent));
        } else {
            reasons.add("Face check not performed (no live photo supplied)");
        }
        reasons.add(in.validationFailed() ? "Deterministic validation FAILED → +" + validationComponent
                : "Deterministic validation passed");
        reasons.add(in.blacklistHit() ? "Blacklist HIT → +" + blacklistComponent : "Blacklist: no match");
        if (in.multipleIdentityFlag()) reasons.add("Multiple-identity match against a different document → +" + multiIdComponent);
        if (in.livenessFailed()) reasons.add("Liveness check FAILED → +" + livenessComponent);

        String level = scaled <= 30 ? "LOW" : scaled <= 65 ? "MEDIUM" : "HIGH";
        reasons.add(String.format("Final risk score %.1f/100 → %s", scaled, level));

        return new Result(scaled, level, reasons);
    }

    private static double clamp(double v) { return Math.max(0.0, Math.min(1.0, v)); }
    private static double round2(double v) { return Math.round(v * 100.0) / 100.0; }
}
