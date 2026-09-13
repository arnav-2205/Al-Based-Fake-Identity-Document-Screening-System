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
@Table(name = "face_embeddings")
@Getter
@Setter
@NoArgsConstructor
public class FaceEmbedding {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "verification_id", nullable = false)
    private Long verificationId;

    @Column(name = "document_number")
    private String documentNumber;

    @Type(JsonType.class)
    @Column(name = "embedding", columnDefinition = "jsonb", nullable = false)
    private List<Double> embedding;

    @Column(name = "created_at", insertable = false, updatable = false)
    private OffsetDateTime createdAt;
}
