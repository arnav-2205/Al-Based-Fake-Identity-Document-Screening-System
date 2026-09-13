package gov.mha.screening.audit;

import jakarta.persistence.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

import java.time.OffsetDateTime;

@Entity
@Table(name = "audit_logs")
@Getter
@Setter
@NoArgsConstructor
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "verification_id")
    private Long verificationId;

    @Column(name = "user_id")
    private Long userId;

    @Column(nullable = false)
    private String action;

    @Column(name = "timestamp")
    private OffsetDateTime timestamp;

    @PrePersist
    public void prePersist() {
        if (timestamp == null) {
            timestamp = OffsetDateTime.now();
        }
    }

    @Column(name = "ip_address")
    private String ipAddress;

    @Column(name = "record_hash", length = 64)
    private String recordHash;

    @Column(name = "blockchain_tx_id")
    private String blockchainTxId;

    @Column(name = "integrity_status")
    private String integrityStatus;
}
