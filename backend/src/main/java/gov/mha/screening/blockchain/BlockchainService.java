package gov.mha.screening.blockchain;

import java.util.Optional;

/**
 * Audit-integrity layer. Only the SHA-256 hash of a verification record is
 * written to the ledger — never images or biometric data (Spec Part 2).
 */
public interface BlockchainService {

    record LedgerRecord(String verificationId, String recordHash, String txId, long timestamp) {}

    /** registerVerification() chaincode call. Returns the transaction id. */
    String registerVerification(String verificationId, String recordHash);

    /** getVerification() chaincode call. */
    Optional<LedgerRecord> getVerification(String verificationId);

    /** verifyIntegrity(): compares a freshly computed hash against the ledger. */
    boolean verifyIntegrity(String verificationId, String currentHash);
}
