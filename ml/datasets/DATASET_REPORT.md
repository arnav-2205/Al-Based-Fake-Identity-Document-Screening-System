# SIH26188 — Dataset Inventory and Safety Compliance Report

**Generated:** 2026-09-02  
**Compliance Standard:** Smart India Hackathon 2026 Defensive ML Security Guidelines  
**Total Storage Footprint:** ~42 MB (Well under 15 GB ceiling)  
**Total Curated Samples:** 3,600 cross-modal images and annotations  

---

## 1. Dataset Breakdown

| Dataset Name | Source | Document Type | Total Samples | Splits (Train/Val/Test) | Purpose |
|---|---|---|---|---|---|
| **Synthetic Passports (TD3)** | In-House Generator | Indian/International Passport | 800 | 560 / 120 / 120 (70/15/15) | OCR, Visual Zone & MRZ Field Extraction |
| **Tampering Pairs** | Multi-Modal Tampering Engine | Passport / ID | 800 (400 Gen + 400 Tamp) | 560 / 120 / 120 | Photo Splicing, Text Manipulation, Stamp Forgery |
| **Immigration Stamps** | StaVer-aligned Generator | Visa & Entry Stamps | 800 (400 Gen + 400 Forg) | 560 / 120 / 120 | Stamp Authenticity Verification |
| **Face Live / Spoof** | Biometric Synthesis Engine | Facial Portraits | 800 (400 Live + 400 Spoof) | 560 / 120 / 120 | Face Embedding & Anti-Spoofing Liveness |
| **MRZ Benchmark Suite** | ICAO 9303 Specs | TD1, TD2, TD3 | 400 Records | 280 / 60 / 60 | Checksum & String Parsing Validation |

---

## 2. Safety and Privacy Compliance Audit

- **Zero Real PII:** All names, dates of birth, passport numbers, and identities are generated purely synthetically. No actual individual's personal data or biometric information is included.
- **Strict Data Leakage Prevention:** Document identities are partitioned strictly by document ID across splits (70% Train, 15% Validation, 15% Test). An identity present in training never appears in validation or test splits.
- **Defensive Splicing:** Tampering pairs represent realistic defensive attack vectors (Photo Replacement, Text Alteration, Stamp Forgery, MRZ Checksum corruption) for model training and robustness verification.
- **Storage Safety:** Total storage utilized is ~42 MB, satisfying the safety constraint (hard cap 15 GB).

---

## 3. Data Integrity & Validation

All generated images and manifest entries have been verified for:
1. Valid PNG headers and dimensions (800x520 for documents, 120x120 for stamps, 160x200 for faces).
2. Complete annotations linking ground truth metadata, labels, and bounding boxes.
3. Matching check-digit parity for genuine MRZ records and expected failure signatures for tampered records.
