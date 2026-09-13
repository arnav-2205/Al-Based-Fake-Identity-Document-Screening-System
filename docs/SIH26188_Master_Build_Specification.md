# SIH26188 — AI-Based Fake Identity & Document Screening System
## Master Build Specification (Final, Consolidated)
**Organization:** Ministry of Home Affairs | **Department:** SSB, Police II Division
**Core stack:** React + Spring Boot + Python/FastAPI (AI) + PostgreSQL + MinIO + Hyperledger Fabric

This document merges everything decided so far — the layered AI architecture, the Spring Boot + blockchain tech stack, the database design, and the specific fraud cases the problem statement names — into one buildable spec.

---

## PART 1 — Fraud Case → Detection Technique Mapping

This is the most important table in the whole document. Every fraud case named in the problem statement must map to a concrete, buildable detection mechanism. If a row here doesn't map to something you can actually implement, cut it or simplify it — don't leave a fraud case "vaguely covered by AI."

| # | Fraud case | Detected by | Exact technique / model |
|---|---|---|---|
| 1 | **Fake / counterfeit document** | Document validation + tamper detection | Document-type classifier (MobileNetV3) confirms structure; overall composite tamper score flags non-genuine layout/fonts/security features |
| 2 | **Photo replacement** | Tamper Detection Service | Error Level Analysis (ELA via Pillow) + EfficientNet-B0 forgery classifier on the photo region; Grad-CAM heatmap shows the exact replaced region |
| 3 | **Text manipulation** | Tamper Detection Service | Font/spacing/baseline consistency check on OCR bounding boxes; ELA on text regions; flags inconsistent character rendering |
| 4 | **DOB modification** | Text manipulation check + Document Validation | Same ELA/font-consistency check on the DOB field specifically, **plus** cross-field consistency: DOB in MRZ vs. DOB in visual zone must match exactly (Spring Boot rule) |
| 5 | **Passport number manipulation** | Document Validation (deterministic, not ML) | **MRZ checksum validation (ICAO 9303 check-digit algorithm)** — passport numbers have a mathematical check digit; a manipulated number fails the checksum instantly. This is your most reliable, explainable detection |
| 6 | **Visa stamp forgery / tampering** | Tamper Detection Service | SIFT/ORB keypoint feature matching (OpenCV) against a reference stamp template library, combined with a ResNet18 genuine-vs-forged stamp classifier |
| 7 | **Identity impersonation** | Face Verification Service | Face embedding (InsightFace/ArcFace) similarity between the live-captured face and the document photo; low similarity → impersonation flag |
| 8 | **Face spoofing** | Face Verification Service (liveness sub-module) | Passive anti-spoofing model (blink detection via dlib landmarks, or a lightweight Silent-Face-Anti-Spoofing model) run **before** trusting the "live face" input to the match step |
| 9 | **Multiple identities (same person, different documents)** | Cross-record correlation (Spring Boot + Postgres) | Store every verified face embedding; on each new verification, run a similarity search against **all stored embeddings** — a match against a *different* document number is a multiple-identity flag |
| 10 | **Expired document** | Document Validation (deterministic) | Simple rule: `expiry_date < current_date` → EXPIRED. No ML needed — must be 100% reliable |
| 11 | **Blacklisted document** | Blacklist Service | Direct lookup of document number/name/DOB against the `blacklist` table (Redis-cached for speed) |
| 12 | **OCR / MRZ / document info mismatch** | Document Validation | Cross-check every field extracted from the MRZ zone against the same field extracted from the visual (non-MRZ) zone of the document — any mismatch is flagged as inconsistent |
| 13 | **Digital document/image tampering** | Tamper Detection Service | EXIF metadata analysis (editing-software signatures, timestamp inconsistencies) + copy-move detection (ORB keypoint duplication) as supporting evidence alongside ELA |
| 14 | **Fake visa** | Document Validation + Tamper Detection | Visa-specific template/format validation (visa number format, entry-type codes) + stamp forgery detection (case 6) applied to the visa stamp specifically |
| 15 | **Unauthorized/fraudulent use of a genuine document** | Face Verification + Blacklist correlation | The document itself passes validation (it's genuine), but face match fails — this is the case where **face verification, not document validation, is the deciding signal**, which is exactly why Module 4 exists as a separate check even after a document "passes" |

**Key insight to state explicitly in your presentation:** no single module catches every fraud type. Case 15 specifically proves why you need *all four* modules — a perfectly genuine, unaltered, non-blacklisted document can still be fraud if the wrong person is holding it. This is a good slide to highlight your system's completeness.

---

## PART 2 — Complete Technology Stack

### Frontend
| Tech | Purpose |
|---|---|
| React 18 + TypeScript | Dashboard SPA |
| Tailwind CSS | Styling |
| Axios | API calls |
| React Router | Navigation |
| Recharts | Risk-score visualizations, trend charts |

### Backend Core — Spring Boot
| Tech | Purpose |
|---|---|
| Java 21, Spring Boot 3.x | Main application server |
| Spring Web | REST controllers |
| Spring WebFlux (`WebClient`) | Parallel non-blocking calls to the 3 Python AI services |
| Spring Data JPA + Hibernate | ORM / database access |
| Lombok | Boilerplate reduction |
| Maven | Build/dependency management |
| Bean Validation (Jakarta) | Input validation, custom MRZ-format annotations |

### Security
| Tech | Purpose |
|---|---|
| Spring Security + JWT | Authentication, stateless sessions |
| BCrypt / Argon2 | Password hashing |
| RBAC (`ADMIN`, `OFFICER`, `INVESTIGATOR`, `AUDITOR`) | Role-scoped endpoints |
| HTTPS/TLS | Transport encryption |
| Rate limiting (Bucket4j or Spring Cloud Gateway filter) | API abuse prevention |
| CORS config | Restrict allowed origins |

### Database & Storage
| Tech | Purpose |
|---|---|
| PostgreSQL 15 | Primary relational store |
| Redis | Blacklist cache, session cache |
| MinIO (S3-compatible) | Document image storage — **never store raw images in Postgres** |

### AI/ML Microservices — Python
| Tech | Purpose |
|---|---|
| Python 3.11 + FastAPI + Uvicorn | AI service framework (one service per module, or one combined service with 3 routers for a leaner build) |
| OpenCV | Preprocessing: deskew, crop, contrast, ROI detection |
| PaddleOCR (PP-OCRv4) | General document OCR |
| Custom MRZ parser | ICAO 9303 checksum validation |
| PyTorch + EfficientNet-B0 | Tamper/forgery classification |
| Pillow | Error Level Analysis |
| InsightFace (ArcFace, buffalo_l) | Face embeddings |
| Anti-spoofing model (Silent-Face-Anti-Spoofing or blink-based) | Liveness check |

### Risk Engine
| Tech | Purpose |
|---|---|
| Java-native weighted rule engine (inside Spring Boot) | Deterministic, explainable base scoring — **no XGBoost/SHAP required for MVP**, keep it simple and defensible |

### Blockchain (Audit Integrity Layer)
| Tech | Purpose |
|---|---|
| Hyperledger Fabric | Permissioned blockchain for tamper-evident audit records |
| Chaincode (JS/TS or Java) | Smart contract functions: `registerVerification()`, `getVerification()`, `verifyIntegrity()`, `getHistory()` |
| Fabric CA | Identity/certificate management for network participants |
| SHA-256 | Cryptographic fingerprint of each verification record, written to the ledger |

**Critical rule: never put document images or raw biometric data on-chain.** Only the SHA-256 hash of the verification record goes to Fabric — this keeps the chain lightweight and avoids storing sensitive PII immutably in a place that (by blockchain design) can never be deleted, which is important for privacy-law compliance.

### DevOps
| Tech | Purpose |
|---|---|
| Docker + Docker Compose | Local multi-service orchestration (frontend, Spring Boot, Python AI, Postgres, Redis, MinIO, Fabric) |
| Git + GitHub | Version control, feature branches per module |

### Testing
| Layer | Tools |
|---|---|
| Spring Boot | JUnit 5, Mockito, Spring Boot Test, Testcontainers |
| Python | pytest |
| API | Postman, Swagger/OpenAPI (springdoc-openapi + FastAPI's built-in docs) |
| Frontend | Vitest/Jest, React Testing Library |
| Security | Manual test cases: invalid JWT, wrong role, oversized file, SQL injection attempt, malformed MRZ input, rate-limit trigger |

---

## PART 3 — System Architecture

```
                              👮 OFFICER
                                  │
                                  ▼
                        ┌──────────────────┐
                        │  React Dashboard  │
                        └────────┬──────────┘
                                 │ HTTPS
                                 ▼
                   ┌───────────────────────────┐
                   │        SPRING BOOT          │
                   │  Spring Security + JWT/RBAC │
                   │  REST APIs · Business Logic │
                   │  Risk Engine · Orchestration│
                   └──────────────┬───────────────┘
                                  │
        ┌─────────────┬───────────┼───────────┬─────────────┐
        ▼             ▼           ▼           ▼             ▼
   PostgreSQL       Redis       MinIO   Python FastAPI   Hyperledger
   (structured)    (cache)    (images)   (AI services)     Fabric
                                              │
                                ┌─────────────┼─────────────┐
                                ▼             ▼             ▼
                              OCR /        Tampering       Face
                              MRZ          Detection    Verification
                                │             │             │
                                └──────────┬──┴─────────────┘
                                           ▼
                                     Results → Spring Boot
                                           │
                             ┌─────────────┼─────────────┐
                             ▼             ▼             ▼
                        Risk Engine   Blacklist DB   Validation Rules
                             │
                             ▼
                       FINAL VERIFICATION RESULT
                             │
                             ▼
                          SHA-256 hash
                             │
                             ▼
                    Hyperledger Fabric ledger
                             │
                             ▼
                    Officer Dashboard (result + audit trail)
```

---

## PART 4 — Database Schema (7 Core Tables)

```
users
──────────────────────────
id PK · officer_id UNIQUE · name · email UNIQUE
password_hash · role · checkpoint_id · is_active
created_at · updated_at

documents
──────────────────────────
id PK · document_type · document_number
file_reference (→ MinIO) · file_hash (SHA-256)
uploaded_by FK→users.id · created_at

extracted_data
──────────────────────────
id PK · document_id FK · name · passport_number
nationality · date_of_birth · gender
issue_date · expiry_date · mrz_data
ocr_confidence · created_at

verification_results          ← the core AI-result table
──────────────────────────
id PK · document_id FK
ocr_status · validation_status
tampering_score · photo_tampering · text_tampering · stamp_tampering
face_match_score · face_match_status · liveness_status
blacklist_status
risk_score · risk_level · final_result · reasons (JSONB)
verified_by FK→users.id · created_at

blacklist                     ← mock watchlist for the prototype
──────────────────────────
id PK · document_number · document_type
reason · status · created_at · updated_at

audit_logs                    ← bridges DB + blockchain
──────────────────────────
id PK · verification_id FK · user_id FK
action · timestamp · ip_address
record_hash · blockchain_tx_id · integrity_status

notifications
──────────────────────────
id PK · verification_id FK · type · recipient
message · status · created_at
```

**Relationships:** `users` 1—N `documents` 1—1 `extracted_data`, `documents` 1—1 `verification_results` 1—N `audit_logs`/`notifications`. `blacklist` is a reference/lookup table, not a child of any verification.

**What goes where (never mix these up):**

| Data | PostgreSQL | MinIO | Blockchain |
|---|:---:|:---:|:---:|
| Officer account, document metadata, OCR/risk results | ✅ | ❌ | ❌ |
| Passport/visa image | ❌ | ✅ | ❌ |
| Verification record hash | ✅ (reference) | ❌ | ✅ |

---

## PART 5 — End-to-End Workflow

1. **Login** — Officer authenticates → Spring Security validates → JWT issued.
2. **Upload** — Officer uploads document image → Spring Boot stores raw file in MinIO, computes SHA-256, creates `documents` row.
3. **Preprocessing** — OpenCV (inside the Python service) deskews/crops/enhances before inference.
4. **Parallel AI inference** — Spring Boot (`WebClient`, `Mono.zip()`) calls OCR, Tamper Detection, and Face Verification **simultaneously**.
5. **Structured extraction** — OCR + MRZ parser results saved to `extracted_data`.
6. **Deterministic validation** — Spring Boot rule engine checks: MRZ checksum, expiry date, DOB plausibility, MRZ-vs-visual-zone consistency (catches fraud cases #4, #5, #9, #10, #12).
7. **Blacklist lookup** — Redis-cached check against `blacklist` (catches #11).
8. **Multi-identity check** — Face embedding compared against all previously stored embeddings in the DB (catches #9).
9. **Risk scoring** — Weighted formula combines all signals into `risk_score` (0–100) and `risk_level` (LOW/MEDIUM/HIGH), with `reasons` stored as structured JSON for explainability.
10. **Persistence + hashing** — Full result saved to `verification_results`; SHA-256 of the record computed.
11. **Blockchain write** — Hash + verification ID sent to Hyperledger Fabric chaincode via the Fabric Gateway; transaction ID stored back in `audit_logs`.
12. **Dashboard display** — Officer sees extracted fields, tamper heatmap, face match score, risk verdict, and reasons.
13. **Officer decision** — CLEAR / SECONDARY SCREENING / DETAIN — logged to `audit_logs` and `notifications`.
14. **Integrity check (on demand)** — Re-hash the current DB record, compare against the blockchain-stored hash; mismatch → tamper alert on the record itself.

---

## PART 6 — Risk Scoring Formula (MVP — Rule-Based, No ML Required)

```
risk_score =
    w1 * tampering_score              (photo + text + stamp, 0–1)
  + w2 * (1 - face_match_score)       (0–1)
  + w3 * (validation_failed ? 1 : 0)  (expiry, checksum, MRZ mismatch)
  + w4 * (blacklist_hit ? 1 : 0)
  + w5 * (multiple_identity_flag ? 1 : 0)
  + w6 * (liveness_failed ? 1 : 0)

Suggested starting weights (tune empirically):
  w1 = 25   w2 = 20   w3 = 20   w4 = 20   w5 = 10   w6 = 5

risk_score → scaled to 0–100
LOW:    0–30
MEDIUM: 31–65
HIGH:   66–100
```

Every score is stored with a `reasons` JSON array like:
```json
["Tamper score 0.82 on photo region", "Face match 0.31 (below 0.5 threshold)", "Blacklist: no match"]
```
This is what makes the score explainable to the officer — never show a bare number without the contributing reasons.

---

## PART 7 — Core API Endpoints

```
POST   /api/auth/login
POST   /api/documents/upload
POST   /api/verification/start
GET    /api/verification/{id}
GET    /api/verification/{id}/audit-trail
POST   /api/verification/{id}/decision      (officer's CLEAR/FLAG/DENY)
GET    /api/investigations/{caseId}
GET    /api/blacklist
POST   /api/blacklist                        (admin only)
GET    /api/audit/{id}
GET    /api/audit/{id}/integrity-check        (re-hash vs. blockchain)
```

---

## PART 8 — MVP Scope vs. Stretch Goals

### MVP (must work reliably in the live demo)
- Passport + one more document type, end-to-end
- MRZ checksum validation + expiry check (deterministic, zero-risk to demo)
- ELA-based tamper detection with heatmap
- Face match (document photo vs. live/second photo)
- Mock blacklist with 2–3 seeded flagged records
- Weighted risk score with visible reasons
- SHA-256 + Hyperledger Fabric write, with a working integrity-check demo (edit a DB record directly, show the mismatch)
- Officer login + role-based dashboard

### Stretch (if time allows)
- Liveness/anti-spoofing on live capture
- Multi-identity detection across stored face embeddings
- Stamp-specific forgery detection (SIFT/ORB template matching)
- Real-time multi-checkpoint simulation via Kafka
- Analytics dashboard (fraud trends, per-checkpoint volume)

**Advice: get the MVP list rock-solid before touching blockchain or stretch AI features.** Judges will test your demo live — a reliable MRZ-checksum + tamper-heatmap + blacklist flow that never breaks beats a fragile system with ten features where three are half-working.

---

## PART 9 — Why This Design Directly Answers the Problem Statement

- **"Reduce verification time from minutes to seconds"** → parallel async AI calls via Spring WebFlux.
- **"Detect forged/tampered documents"** → Part 1's fraud-case mapping, one technique per case.
- **"Standardize screening decisions"** → deterministic rule engine + explainable weighted risk score, not a black-box model.
- **"Digital trail for investigations"** → `audit_logs` + Hyperledger Fabric, with a live integrity-check demo.
- **"High passenger volume"** → Kafka ingestion buffer (stretch) shows you've thought about throughput even if not fully built for the demo.
