package gov.mha.screening.verification;

import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.Type;

import java.time.OffsetDateTime;
import java.util.List;

@Entity
@Table(name = "verification_results")
@Getter
@Setter
@NoArgsConstructor
public class VerificationResult {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "document_id", nullable = false)
    private Long documentId;

    @Column(name = "selected_type")
    private String selectedType;

    @Column(name = "detected_type")
    private String detectedType;

    @Column(name = "detection_confidence")
    private Double detectionConfidence;

    @Column(name = "ocr_status")
    private String ocrStatus;

    @Column(name = "validation_status")
    private String validationStatus;

    @Column(name = "tampering_score")
    private Double tamperingScore;
    @Column(name = "photo_tampering")
    private Double photoTampering;
    @Column(name = "text_tampering")
    private Double textTampering;
    @Column(name = "stamp_tampering")
    private Double stampTampering;

    @Column(name = "photo_forgery_status")
    private String photoForgeryStatus;
    @Column(name = "photo_forgery_confidence")
    private Double photoForgeryConfidence;
    @Type(JsonType.class)
    @Column(name = "photo_forgery_reasons", columnDefinition = "jsonb")
    private List<String> photoForgeryReasons;

    @Column(name = "text_manipulation_status")
    private String textManipulationStatus;
    @Column(name = "text_manipulation_confidence")
    private Double textManipulationConfidence;
    @Type(JsonType.class)
    @Column(name = "text_manipulation_fields", columnDefinition = "jsonb")
    private List<String> textManipulationFields;
    @Type(JsonType.class)
    @Column(name = "text_manipulation_reasons", columnDefinition = "jsonb")
    private List<String> textManipulationReasons;

    @Column(name = "stamp_forgery_status")
    private String stampForgeryStatus;
    @Column(name = "stamp_forgery_confidence")
    private Double stampForgeryConfidence;
    @Type(JsonType.class)
    @Column(name = "stamp_forgery_reasons", columnDefinition = "jsonb")
    private List<String> stampForgeryReasons;

    @Column(name = "metadata_status")
    private String metadataStatus;
    @Column(name = "metadata_confidence")
    private Double metadataConfidence;
    @Type(JsonType.class)
    @Column(name = "metadata_reasons", columnDefinition = "jsonb")
    private List<String> metadataReasons;

    @Column(name = "viz_mrz_status")
    private String vizMrzStatus;
    @Type(JsonType.class)
    @Column(name = "viz_mrz_matched_fields", columnDefinition = "jsonb")
    private List<String> vizMrzMatchedFields;
    @Type(JsonType.class)
    @Column(name = "viz_mrz_mismatches", columnDefinition = "jsonb")
    private List<gov.mha.screening.validation.VizMrzCrossValidation.FieldMismatch> vizMrzMismatches;
    @Type(JsonType.class)
    @Column(name = "viz_mrz_reasons", columnDefinition = "jsonb")
    private List<String> vizMrzReasons;

    @Column(name = "expiry_status")
    private String expiryStatus;
    @Column(name = "expiry_date_validated")
    private java.time.LocalDate expiryDateValidated;
    @Column(name = "expiry_days_remaining")
    private Long expiryDaysRemaining;
    @Column(name = "expiry_source")
    private String expirySource;

    @Type(JsonType.class)
    @Column(name = "visa_verification", columnDefinition = "jsonb")
    private gov.mha.screening.verification.VerificationDtos.VisaVerificationView visaVerification;

    @Type(JsonType.class)
    @Column(name = "driving_licence_verification", columnDefinition = "jsonb")
    private gov.mha.screening.verification.VerificationDtos.DrivingLicenceVerificationView drivingLicenceVerification;

    @Type(JsonType.class)
    @Column(name = "national_id_verification", columnDefinition = "jsonb")
    private gov.mha.screening.verification.VerificationDtos.NationalIdVerificationView nationalIdVerification;

    @Type(JsonType.class)
    @Column(name = "permit_verification", columnDefinition = "jsonb")
    private gov.mha.screening.verification.VerificationDtos.PermitVerificationView permitVerification;


    @Column(name = "face_match_score")


    private Double faceMatchScore;
    @Column(name = "face_match_status")
    private String faceMatchStatus;
    @Column(name = "liveness_status")
    private String livenessStatus;

    @Column(name = "blacklist_status")
    private String blacklistStatus;

    @Column(name = "risk_score")
    private Double riskScore;
    @Column(name = "risk_level")
    private String riskLevel;
    @Column(name = "final_result")
    private String finalResult;

    @Type(JsonType.class)
    @Column(name = "risk_assessment", columnDefinition = "jsonb")
    private gov.mha.screening.risk.RiskEngine.RiskAssessment riskAssessment;

    @Type(JsonType.class)
    @Column(name = "reasons", columnDefinition = "jsonb")
    private List<String> reasons;

    @Column(name = "verified_by")
    private Long verifiedBy;

    @Column(name = "created_at", updatable = false)
    private OffsetDateTime createdAt;

    @PrePersist
    public void prePersist() {
        if (createdAt == null) {
            createdAt = OffsetDateTime.now();
        }
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getDocumentId() { return documentId; }
    public void setDocumentId(Long documentId) { this.documentId = documentId; }
    public String getSelectedType() { return selectedType; }
    public void setSelectedType(String selectedType) { this.selectedType = selectedType; }
    public String getDetectedType() { return detectedType; }
    public void setDetectedType(String detectedType) { this.detectedType = detectedType; }
    public Double getDetectionConfidence() { return detectionConfidence; }
    public void setDetectionConfidence(Double detectionConfidence) { this.detectionConfidence = detectionConfidence; }
    public String getOcrStatus() { return ocrStatus; }
    public void setOcrStatus(String ocrStatus) { this.ocrStatus = ocrStatus; }
    public String getValidationStatus() { return validationStatus; }
    public void setValidationStatus(String validationStatus) { this.validationStatus = validationStatus; }
    public Double getTamperingScore() { return tamperingScore; }
    public void setTamperingScore(Double tamperingScore) { this.tamperingScore = tamperingScore; }
    public Double getPhotoTampering() { return photoTampering; }
    public void setPhotoTampering(Double photoTampering) { this.photoTampering = photoTampering; }
    public Double getTextTampering() { return textTampering; }
    public void setTextTampering(Double textTampering) { this.textTampering = textTampering; }
    public Double getStampTampering() { return stampTampering; }
    public void setStampTampering(Double stampTampering) { this.stampTampering = stampTampering; }
    public String getPhotoForgeryStatus() { return photoForgeryStatus; }
    public void setPhotoForgeryStatus(String photoForgeryStatus) { this.photoForgeryStatus = photoForgeryStatus; }
    public Double getPhotoForgeryConfidence() { return photoForgeryConfidence; }
    public void setPhotoForgeryConfidence(Double photoForgeryConfidence) { this.photoForgeryConfidence = photoForgeryConfidence; }
    public List<String> getPhotoForgeryReasons() { return photoForgeryReasons; }
    public void setPhotoForgeryReasons(List<String> photoForgeryReasons) { this.photoForgeryReasons = photoForgeryReasons; }
    public String getTextManipulationStatus() { return textManipulationStatus; }
    public void setTextManipulationStatus(String textManipulationStatus) { this.textManipulationStatus = textManipulationStatus; }
    public Double getTextManipulationConfidence() { return textManipulationConfidence; }
    public void setTextManipulationConfidence(Double textManipulationConfidence) { this.textManipulationConfidence = textManipulationConfidence; }
    public List<String> getTextManipulationFields() { return textManipulationFields; }
    public void setTextManipulationFields(List<String> textManipulationFields) { this.textManipulationFields = textManipulationFields; }
    public List<String> getTextManipulationReasons() { return textManipulationReasons; }
    public void setTextManipulationReasons(List<String> textManipulationReasons) { this.textManipulationReasons = textManipulationReasons; }
    public String getStampForgeryStatus() { return stampForgeryStatus; }
    public void setStampForgeryStatus(String stampForgeryStatus) { this.stampForgeryStatus = stampForgeryStatus; }
    public Double getStampForgeryConfidence() { return stampForgeryConfidence; }
    public void setStampForgeryConfidence(Double stampForgeryConfidence) { this.stampForgeryConfidence = stampForgeryConfidence; }
    public List<String> getStampForgeryReasons() { return stampForgeryReasons; }
    public void setStampForgeryReasons(List<String> stampForgeryReasons) { this.stampForgeryReasons = stampForgeryReasons; }
    public String getMetadataStatus() { return metadataStatus; }
    public void setMetadataStatus(String metadataStatus) { this.metadataStatus = metadataStatus; }
    public Double getMetadataConfidence() { return metadataConfidence; }
    public void setMetadataConfidence(Double metadataConfidence) { this.metadataConfidence = metadataConfidence; }
    public List<String> getMetadataReasons() { return metadataReasons; }
    public void setMetadataReasons(List<String> metadataReasons) { this.metadataReasons = metadataReasons; }
    public String getVizMrzStatus() { return vizMrzStatus; }
    public void setVizMrzStatus(String vizMrzStatus) { this.vizMrzStatus = vizMrzStatus; }
    public List<String> getVizMrzMatchedFields() { return vizMrzMatchedFields; }
    public void setVizMrzMatchedFields(List<String> vizMrzMatchedFields) { this.vizMrzMatchedFields = vizMrzMatchedFields; }
    public List<gov.mha.screening.validation.VizMrzCrossValidation.FieldMismatch> getVizMrzMismatches() { return vizMrzMismatches; }
    public void setVizMrzMismatches(List<gov.mha.screening.validation.VizMrzCrossValidation.FieldMismatch> vizMrzMismatches) { this.vizMrzMismatches = vizMrzMismatches; }
    public List<String> getVizMrzReasons() { return vizMrzReasons; }
    public void setVizMrzReasons(List<String> vizMrzReasons) { this.vizMrzReasons = vizMrzReasons; }
    public String getExpiryStatus() { return expiryStatus; }
    public void setExpiryStatus(String expiryStatus) { this.expiryStatus = expiryStatus; }
    public java.time.LocalDate getExpiryDateValidated() { return expiryDateValidated; }
    public void setExpiryDateValidated(java.time.LocalDate expiryDateValidated) { this.expiryDateValidated = expiryDateValidated; }
    public Long getExpiryDaysRemaining() { return expiryDaysRemaining; }
    public void setExpiryDaysRemaining(Long expiryDaysRemaining) { this.expiryDaysRemaining = expiryDaysRemaining; }
    public String getExpirySource() { return expirySource; }
    public void setExpirySource(String expirySource) { this.expirySource = expirySource; }
    public gov.mha.screening.verification.VerificationDtos.VisaVerificationView getVisaVerification() { return visaVerification; }
    public void setVisaVerification(gov.mha.screening.verification.VerificationDtos.VisaVerificationView visaVerification) { this.visaVerification = visaVerification; }
    public gov.mha.screening.verification.VerificationDtos.DrivingLicenceVerificationView getDrivingLicenceVerification() { return drivingLicenceVerification; }
    public void setDrivingLicenceVerification(gov.mha.screening.verification.VerificationDtos.DrivingLicenceVerificationView drivingLicenceVerification) { this.drivingLicenceVerification = drivingLicenceVerification; }
    public gov.mha.screening.verification.VerificationDtos.NationalIdVerificationView getNationalIdVerification() { return nationalIdVerification; }
    public void setNationalIdVerification(gov.mha.screening.verification.VerificationDtos.NationalIdVerificationView nationalIdVerification) { this.nationalIdVerification = nationalIdVerification; }
    public gov.mha.screening.verification.VerificationDtos.PermitVerificationView getPermitVerification() { return permitVerification; }
    public void setPermitVerification(gov.mha.screening.verification.VerificationDtos.PermitVerificationView permitVerification) { this.permitVerification = permitVerification; }

    public Double getFaceMatchScore() { return faceMatchScore; }


    public void setFaceMatchScore(Double faceMatchScore) { this.faceMatchScore = faceMatchScore; }
    public String getFaceMatchStatus() { return faceMatchStatus; }
    public void setFaceMatchStatus(String faceMatchStatus) { this.faceMatchStatus = faceMatchStatus; }
    public String getLivenessStatus() { return livenessStatus; }
    public void setLivenessStatus(String livenessStatus) { this.livenessStatus = livenessStatus; }
    public String getBlacklistStatus() { return blacklistStatus; }
    public void setBlacklistStatus(String blacklistStatus) { this.blacklistStatus = blacklistStatus; }
    public Double getRiskScore() { return riskScore; }
    public void setRiskScore(Double riskScore) { this.riskScore = riskScore; }
    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }
    public String getFinalResult() { return finalResult; }
    public void setFinalResult(String finalResult) { this.finalResult = finalResult; }
    public gov.mha.screening.risk.RiskEngine.RiskAssessment getRiskAssessment() { return riskAssessment; }
    public void setRiskAssessment(gov.mha.screening.risk.RiskEngine.RiskAssessment riskAssessment) { this.riskAssessment = riskAssessment; }
    public List<String> getReasons() { return reasons; }
    public void setReasons(List<String> reasons) { this.reasons = reasons; }
    public Long getVerifiedBy() { return verifiedBy; }
    public void setVerifiedBy(Long verifiedBy) { this.verifiedBy = verifiedBy; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
