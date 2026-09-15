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
    public List<String> getReasons() { return reasons; }
    public void setReasons(List<String> reasons) { this.reasons = reasons; }
    public Long getVerifiedBy() { return verifiedBy; }
    public void setVerifiedBy(Long verifiedBy) { this.verifiedBy = verifiedBy; }
    public OffsetDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(OffsetDateTime createdAt) { this.createdAt = createdAt; }
}
