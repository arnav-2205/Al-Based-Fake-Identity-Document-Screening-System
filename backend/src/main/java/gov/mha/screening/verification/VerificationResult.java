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
}
