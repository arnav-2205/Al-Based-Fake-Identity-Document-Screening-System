# Architecture

```
Officer ──HTTPS──> React SPA ──/api──> Spring Boot ──┬── PostgreSQL (structured)
                                                     ├── Redis (blacklist cache)
                                                     ├── MinIO (document images)
                                                     ├── FastAPI AI service ──┬── /ocr/extract
                                                     │                        ├── /tamper/analyze
                                                     │                        └── /face/verify
                                                     └── Hyperledger Fabric (SHA-256 audit hash)
```

## Request flow (POST /api/verification/start)

1. `DocumentController` already stored the raw image in MinIO + a `documents` row with its SHA-256.
2. `VerificationService.start()`:
   - pulls the image bytes from MinIO
   - `AiClient.analyzeAll()` — **parallel** `Mono.zip(ocr, tamper, face)` to the AI service
   - `ValidationEngine` — deterministic: ICAO 9303 MRZ check digits, expiry, cross-zone consistency, DOB plausibility
   - `BlacklistService` — Redis-cached lookup by document number and by name+DOB
   - multi-identity — cosine similarity of the new face embedding against every stored embedding
   - `RiskEngine` — weighted formula (Spec Part 6) → score 0–100, level LOW/MEDIUM/HIGH, `reasons[]`
   - persists `extracted_data` + `verification_results` (+ `face_embeddings`)
   - SHA-256 of a canonical subset of the result → `BlockchainService.registerVerification()` → tx id
   - `AuditService.record()` writes `audit_logs` with the hash + tx id
   - HIGH risk → `NotificationService`
3. Response: extracted fields, per-region tamper scores, ELA heatmap (base64), face/liveness, risk verdict, reasons, record hash, tx id.

## Fraud-case coverage

See `SIH26188_Master_Build_Specification.md` Part 1. Implemented signals:

| Case | Where |
|---|---|
| #4 DOB modification, #5 passport-number, #12 MRZ vs visual | `validation/ValidationEngine` + `validation/Mrz` |
| #10 expired | `ValidationEngine` |
| #11 blacklisted | `blacklist/BlacklistService` |
| #9 multiple identities | `verification/VerificationService.checkMultiIdentity` + `face_embeddings` |
| #2 photo, #3 text, #13 digital tampering | `ai-service` ELA + EXIF (`services/ela.py`, `services/exif_check.py`) |
| #1 counterfeit, #6 stamp forgery | `ai-service/services/tamper_model.py` (CNN hooks — TODO weights) |
| #7 impersonation, #8 spoofing, #15 genuine-doc-wrong-person | `ai-service/services/face_engine.py` |

## Integrity-check demo

1. Run a verification, note the `verificationId`.
2. `UPDATE verification_results SET risk_level='LOW', final_result='CLEAR' WHERE id=<id>;`
3. `GET /api/verification/<id>/integrity-check` → `integrityStatus: "TAMPERED"` because the
   re-hash no longer matches the value on the ledger.
