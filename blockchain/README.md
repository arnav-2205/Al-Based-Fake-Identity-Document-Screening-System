# Hyperledger Fabric — Audit Integrity Layer

Only the **SHA-256 hash** of each verification record is written to the ledger.
Never images, never biometrics (Master Build Spec, Part 2).

## Contents

```
chaincode/verification/     Node.js chaincode: registerVerification, getVerification,
                            verifyIntegrity, getHistory
network/                    place Fabric test-network here (see below)
```

## Bring up a local network (Fabric samples)

```bash
# one-time
curl -sSL https://raw.githubusercontent.com/hyperledger/fabric/main/scripts/bootstrap.sh | bash -s -- 2.5.9 1.5.12
mv fabric-samples/test-network network/

cd network
./network.sh up createChannel -c screeningchannel -ca
./network.sh deployCC -c screeningchannel \
    -ccn verification \
    -ccp ../chaincode/verification \
    -ccl javascript
```

Then set `FABRIC_ENABLED=true` for the backend and finish wiring
`FabricBlockchainService` (Fabric Gateway SDK — see its TODO block).

Until then the backend uses `InMemoryBlockchainService`, which is enough to
demo the integrity check: create a verification, edit the `verification_results`
row directly in Postgres, call `GET /api/verification/{id}/integrity-check`,
and watch it report `TAMPERED`.
