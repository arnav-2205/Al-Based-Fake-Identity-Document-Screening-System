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
            String mrz, Double ocrConfidence, Map<String, Object> visualZone,
            String documentCategory, String documentSubtype,
            List<String> applicableFields, List<String> applicableChecks
    ) {}

    public record VizMrzCrossValidationView(
            String status,
            List<String> matchedFields,
            List<FieldMismatchView> mismatches,
            List<String> reasons
    ) {
        public record FieldMismatchView(String field, String vizValue, String mrzValue) {}
    }

    public record ExpiryValidationView(
            String status,
            String expiryDate,
            Long daysRemaining,
            String source
    ) {}

    public record CandidateStampRegionView(
            List<Integer> bbox,
            Double inkRatio,
            String inkType,
            Boolean suspicious,
            List<String> anomalyReasons
    ) {}

    public record StampForgeryView(
            String status,
            Double confidence,
            List<CandidateStampRegionView> candidateStampRegions,
            List<String> reasons
    ) {}

    public record MetadataAnalysisView(
            String status,
            Double confidence,
            List<String> signals,
            Map<String, Object> metadata,
            List<String> reasons
    ) {}

    public record RiskComponentView(
            String code,
            String label,
            Double points,
            Boolean triggered,
            String reason
    ) {}

    public record RiskAssessmentView(
            Double score,
            String level,
            List<RiskComponentView> components,
            List<RiskComponentView> triggeredComponents,
            String decision,
            List<String> decisionBasis,
            String summary,
            Boolean securityOverrideTriggered,
            String securityOverrideReason
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
            String photoForgeryStatus,
            Double photoForgeryConfidence,
            List<String> photoForgeryReasons,
            String textManipulationStatus,
            Double textManipulationConfidence,
            List<String> textManipulationFields,
            List<String> textManipulationReasons,
            String stampForgeryStatus,
            Double stampForgeryConfidence,
            List<String> stampForgeryReasons,
            String metadataStatus,
            Double metadataConfidence,
            List<String> metadataReasons,
            MetadataAnalysisView metadataAnalysis,
            VizMrzCrossValidationView vizMrzCrossValidation,
            ExpiryValidationView expiryValidation,
            RiskAssessmentView riskAssessment,
            String elaHeatmapBase64,
            Double faceMatchScore,
            String faceMatchStatus,
            String livenessStatus,
            String blacklistStatus,
            String storedIdentityMatchStatus,
            String storedIdentityMatchDetail,
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
