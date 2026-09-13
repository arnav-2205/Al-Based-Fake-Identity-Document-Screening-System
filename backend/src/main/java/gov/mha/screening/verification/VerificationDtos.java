package gov.mha.screening.verification;

import java.time.OffsetDateTime;
import java.util.List;
import java.util.Map;

public final class VerificationDtos {

    private VerificationDtos() {}

    public record StartRequest(Long documentId) {}

    public record ExtractedView(
            String name, String passportNumber, String nationality,
            String dateOfBirth, String gender, String issueDate, String expiryDate,
            String mrz, Double ocrConfidence, Map<String, Object> visualZone
    ) {}

    public record VerificationView(
            Long verificationId,
            Long documentId,
            String documentType,
            ExtractedView extracted,
            String ocrStatus,
            String validationStatus,
            Double tamperingScore,
            Double photoTampering,
            Double textTampering,
            Double stampTampering,
            String elaHeatmapBase64,
            Double faceMatchScore,
            String faceMatchStatus,
            String livenessStatus,
            String blacklistStatus,
            Double riskScore,
            String riskLevel,
            String finalResult,
            Boolean securityOverrideTriggered,
            String securityOverrideReason,
            List<String> reasons,
            String recordHash,
            String blockchainTxId,
            OffsetDateTime createdAt
    ) {}

    public record DecisionRequest(String decision, String notes) {} // CLEAR | SECONDARY_SCREENING | DETAIN
}
