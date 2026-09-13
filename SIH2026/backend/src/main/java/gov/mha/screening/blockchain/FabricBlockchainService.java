package gov.mha.screening.blockchain;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.util.Optional;

/**
 * Hyperledger Fabric gateway (Spec Part 2 — Blockchain).
 *
 * TODO: wire the Fabric Gateway SDK (org.hyperledger.fabric:fabric-gateway).
 *   - load connection profile + MSP identity from FABRIC_* env / mounted certs
 *   - Gateway.newInstance(...).getNetwork(channel).getContract(chaincode)
 *   - contract.submitTransaction("registerVerification", verificationId, recordHash)
 *   - contract.evaluateTransaction("getVerification", verificationId)
 *   - contract.evaluateTransaction("verifyIntegrity", verificationId, currentHash)
 *
 * The chaincode itself lives in ../../blockchain/chaincode/verification.
 */
@Service
@Slf4j
@ConditionalOnProperty(name = "app.blockchain.enabled", havingValue = "true")
public class FabricBlockchainService implements BlockchainService {

    @Override
    public String registerVerification(String verificationId, String recordHash) {
        throw new UnsupportedOperationException(
                "Fabric gateway not wired yet — set app.blockchain.enabled=false to use the in-memory ledger");
    }

    @Override
    public Optional<LedgerRecord> getVerification(String verificationId) {
        throw new UnsupportedOperationException("Fabric gateway not wired yet");
    }

    @Override
    public boolean verifyIntegrity(String verificationId, String currentHash) {
        throw new UnsupportedOperationException("Fabric gateway not wired yet");
    }
}
