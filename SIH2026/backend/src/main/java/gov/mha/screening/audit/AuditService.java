package gov.mha.screening.audit;

import gov.mha.screening.blockchain.BlockchainService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
@RequiredArgsConstructor
public class AuditService {

    private final AuditLogRepository repo;
    private final BlockchainService blockchain;

    @Transactional
    public AuditLog record(Long verificationId, Long userId, String action, String ip,
                           String recordHash, String txId, String integrityStatus) {
        AuditLog log = new AuditLog();
        log.setVerificationId(verificationId);
        log.setUserId(userId);
        log.setAction(action);
        log.setIpAddress(ip);
        log.setRecordHash(recordHash);
        log.setBlockchainTxId(txId);
        log.setIntegrityStatus(integrityStatus);
        return repo.save(log);
    }

    public List<AuditLog> trail(Long verificationId) {
        return repo.findByVerificationIdOrderByTimestampAsc(verificationId);
    }

    public List<AuditLog> all() {
        return repo.findAll(org.springframework.data.domain.Sort.by(org.springframework.data.domain.Sort.Direction.DESC, "timestamp"));
    }

    /** Re-hash vs. ledger (Spec Part 5, step 14). */
    public boolean integrityCheck(Long verificationId, String currentHash) {
        return blockchain.verifyIntegrity(String.valueOf(verificationId), currentHash);
    }
}
