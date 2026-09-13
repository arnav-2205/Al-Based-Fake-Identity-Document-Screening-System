package gov.mha.screening.extraction;

import io.hypersistence.utils.hibernate.type.json.JsonType;
import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;
import org.hibernate.annotations.Type;

import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.Map;

@Entity
@Table(name = "extracted_data")
@Getter
@Setter
@NoArgsConstructor
public class ExtractedData {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "document_id", nullable = false)
    private Long documentId;

    private String name;

    @Column(name = "passport_number")
    private String passportNumber;

    private String nationality;

    @Column(name = "date_of_birth")
    private LocalDate dateOfBirth;

    private String gender;

    @Column(name = "issue_date")
    private LocalDate issueDate;

    @Column(name = "expiry_date")
    private LocalDate expiryDate;

    @Column(name = "mrz_data", columnDefinition = "text")
    private String mrzData;

    @Type(JsonType.class)
    @Column(name = "visual_zone", columnDefinition = "jsonb")
    private Map<String, Object> visualZone;

    @Column(name = "ocr_confidence")
    private Double ocrConfidence;

    @Column(name = "created_at", insertable = false, updatable = false)
    private OffsetDateTime createdAt;
}
