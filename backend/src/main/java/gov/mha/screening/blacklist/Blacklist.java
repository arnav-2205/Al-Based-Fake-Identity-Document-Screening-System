package gov.mha.screening.blacklist;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.LocalDate;
import java.time.OffsetDateTime;

@Entity
@Table(name = "blacklist")
@Getter
@Setter
@NoArgsConstructor
public class Blacklist {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "document_number")
    private String documentNumber;

    @Column(name = "document_type")
    private String documentType;

    private String name;

    @Column(name = "date_of_birth")
    private LocalDate dateOfBirth;

    private String reason;

    private String status = "ACTIVE";

    @Column(name = "created_at", insertable = false, updatable = false)
    private OffsetDateTime createdAt;

    @Column(name = "updated_at", insertable = false, updatable = false)
    private OffsetDateTime updatedAt;
}
