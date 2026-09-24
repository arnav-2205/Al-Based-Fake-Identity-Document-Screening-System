# 🛡️ SIH26188 — Demo Credentials & Testing Guide

This document lists the pre-seeded demo user accounts, watchlist records, and sample inputs configured for testing the **AI-Based Fake Identity & Document Screening System**.

---

## 🔐 Demo User Credentials

The system initializes these four accounts upon startup in the database.

| Role | Username / Officer ID | Password | Name | Checkpoint / Office | Permissions & Responsibilities |
|------|-----------------------|----------|------|---------------------|--------------------------------|
| **Officer** | `officer1` | `officer123` | Officer R. Sharma | `ICP-ATTARI` | Uploads documents, triggers live webcam biometric captures, conducts border document inspections. |
| **Admin** | `admin` | `admin123` | System Administrator | `HQ` | Full system access, user management, configuration, system analytics, and system audit logs. |
| **Investigator** | `investigator1` | `invest123` | Investigator P. Nair | `HQ` | Reviews flagged fraudulent cases, analyzes composite forensic tampering reports, manages watchlist hits. |
| **Auditor** | `auditor1` | `audit123` | Auditor S. Rao | `HQ` | Inspects immutable SHA-256 chain-of-custody ledgers, verifies blockchain records, ensures regulatory compliance. |

---

## 🚨 Pre-Seeded Watchlist / Blacklist Entries

These documents are pre-loaded into the system's watchlists to trigger instant security flags during screening:

| Document Number | Type | Subject Name | Date of Birth | Reason / Notice | Status |
|-----------------|------|--------------|---------------|-----------------|--------|
| `P1234567` | `PASSPORT` | John Fictitious | `1985-04-12` | INTERPOL Red Notice — Identity Fraud | `ACTIVE` |
| `X9988776` | `PASSPORT` | Anon Suspect | `1990-11-02` | Watchlist — Multiple forged border entries | `ACTIVE` |
| `V0001111` | `VISA` | Test Forged Visa | `1978-01-30` | Known counterfeit visa serial batch | `ACTIVE` |

---

## 📁 Sample Inputs for Testing

Pre-generated test documents and biometric selfies are available in the [`sample_inputs/`](file:///c:/Users/arnav/OneDrive/Desktop/SIH2/sample_inputs) folder:

| File Name | Intended Behavior | Expected Verdict |
|-----------|-------------------|------------------|
| `01_genuine_passport.png` + `05_live_subject_photo.png` | Authentic document with matching face | `CLEAR` / Low Risk |
| `02_forged_ela_passport.png` + `05_live_subject_photo.png` | Photo replacement anomaly detected via ELA | `REJECT` / High Risk |
| `03_text_tampered_passport.png` + `05_live_subject_photo.png` | Font inconsistency and digital text editing | `MANUAL_REVIEW` / Medium Risk |
| `04_watchlist_hit_passport.png` + `06_impostor_live_photo.png` | Blacklisted passport number + facial mismatch | `REJECT` / Critical Risk |

---

## 🌐 Active Service Endpoints

* **Frontend Dashboard:** [http://localhost:5173](http://localhost:5173)
* **Backend API & Swagger:** [http://localhost:8080/swagger-ui.html](http://localhost:8080/swagger-ui.html)
* **AI Microservice:** [http://127.0.0.1:8000](http://127.0.0.1:8000) (Docs at [/docs](http://127.0.0.1:8000/docs))
