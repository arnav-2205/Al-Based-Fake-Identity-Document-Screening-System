package gov.mha.screening.blockchain;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Fallback used when Fabric is not running (app.blockchain.enabled=false).
 * Behaves like an append-only ledger so the integrity-check demo still works:
 * edit the DB row directly, re-hash, and the comparison fails.
 */
@Service
@Slf4j
@ConditionalOnProperty(name = "app.blockchain.enabled", havingValue = "false", matchIfMissing = true)
public class InMemoryBlockchainService implements BlockchainService {

    private final Map<String, LedgerRecord> ledger = new ConcurrentHashMap<>();

    @Override
    public String registerVerification(String verificationId, String recordHash) {
        String txId = "mem-" + UUID.randomUUID();
        ledger.put(verificationId, new LedgerRecord(verificationId, recordHash, txId, System.currentTimeMillis()));
        log.info("[in-memory ledger] registered {} -> {} ({})", verificationId, recordHash, txId);
        return txId;
    }

    @Override
    public Optional<LedgerRecord> getVerification(String verificationId) {
        return Optional.ofNullable(ledger.get(verificationId));
    }

    @Override
    public boolean verifyIntegrity(String verificationId, String currentHash) {
        return getVerification(verificationId)
                .map(r -> r.recordHash().equals(currentHash))
                .orElse(false);
    }
}
