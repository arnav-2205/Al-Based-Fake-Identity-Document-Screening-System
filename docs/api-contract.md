# API Contract

Base URL: `http://localhost:8080`  ·  Auth: `Authorization: Bearer <jwt>` (except `/api/auth/*`)

Full interactive spec at `/swagger-ui.html`.

## Auth

### POST /api/auth/login
```json
{ "officerId": "officer1", "password": "password" }
```
→ `200`
```json
{ "token": "eyJ...", "officerId": "officer1", "name": "Officer R. Sharma", "role": "OFFICER" }
```

### POST /api/auth/dev/reset-passwords
Non-prod. Sets the seeded accounts to the README passwords. → `{ "status": "ok" }`

## Documents

### POST /api/documents/upload  `multipart/form-data`
| part | type |
|---|---|
| `documentType` | text (PASSPORT/VISA/NATIONAL_ID) |
| `file` | image |

→ `{ "documentId": 1, "documentType": "PASSPORT", "fileHash": "...", "fileReference": "docs/..." }`

Roles: OFFICER, ADMIN, INVESTIGATOR

## Verification

### POST /api/verification/start  `multipart/form-data`
| part | type | required |
|---|---|---|
| `documentId` | number | yes |
| `liveFace` | image | no |

→ `VerificationView` (see below). Roles: OFFICER, ADMIN, INVESTIGATOR

### GET /api/verification/{id} → `VerificationView`
### GET /api/verification/{id}/heatmap → `{ "elaHeatmapBase64": "..." }`
### GET /api/verification/{id}/audit-trail → `AuditLog[]`
### GET /api/verification/{id}/integrity-check → `{ "integrityStatus": "INTACT"|"TAMPERED", "currentHash": "...", "ledgerHash": "..." }`
### POST /api/verification/{id}/decision
```json
{ "decision": "CLEAR" | "SECONDARY_SCREENING" | "DETAIN", "notes": "optional" }
```

### VerificationView
```json
{
  "verificationId": 1,
  "documentId": 1,
  "documentType": "PASSPORT",
  "extracted": {
    "name": "ANNA MARIA ERIKSSON",
    "passportNumber": "L898902C3",
    "nationality": "UTO",
    "dateOfBirth": "1974-08-12",
    "gender": "F",
    "expiryDate": "2012-04-15",
    "mrz": "P<UTO...\nL898902C36UTO...",
    "ocrConfidence": 0.5
  },
  "ocrStatus": "OK",
  "validationStatus": "FAIL",
  "tamperingScore": 0.12,
  "photoTampering": 0.03,
  "textTampering": 0.08,
  "stampTampering": 0.00,
  "elaHeatmapBase64": "iVBORw0KGgo...",
  "faceMatchScore": 0.0,
  "faceMatchStatus": "UNKNOWN",
  "livenessStatus": "UNKNOWN",
  "blacklistStatus": "CLEAR",
  "riskScore": 20.0,
  "riskLevel": "LOW",
  "finalResult": "MANUAL_REVIEW",
  "reasons": ["MRZ check digits: all valid", "Document EXPIRED on 2012-04-15", "..."],
  "recordHash": "9f2c...",
  "blockchainTxId": "mem-...",
  "createdAt": "2026-09-01T10:00:00Z"
}
```

## Blacklist

### GET /api/blacklist → `Blacklist[]`  (any authenticated role)
### POST /api/blacklist  (ADMIN)
```json
{ "documentNumber": "P999", "documentType": "PASSPORT", "name": "X", "dateOfBirth": "1990-01-01", "reason": "..." }
```

## Audit

### GET /api/audit/{verificationId} → `AuditLog[]`
### GET /api/audit/{verificationId}/integrity-check → integrity result

Roles: ADMIN, INVESTIGATOR, AUDITOR
