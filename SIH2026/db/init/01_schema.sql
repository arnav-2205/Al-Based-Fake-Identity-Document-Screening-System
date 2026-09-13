-- SIH26188 — Core schema (7 tables). See Master Build Spec Part 4.
-- Applied automatically by the postgres container on first start.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. users -------------------------------------------------------------
CREATE TABLE users (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    officer_id     VARCHAR(64)  NOT NULL UNIQUE,
    name           VARCHAR(200) NOT NULL,
    email          VARCHAR(200) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    role           VARCHAR(32)  NOT NULL CHECK (role IN ('ADMIN','OFFICER','INVESTIGATOR','AUDITOR')),
    checkpoint_id  VARCHAR(64),
    is_active      BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- 2. documents ---------------------------------------------------------
CREATE TABLE documents (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_type   VARCHAR(32)  NOT NULL,          -- PASSPORT, VISA, NATIONAL_ID ...
    document_number VARCHAR(64),
    file_reference  VARCHAR(512) NOT NULL,          -- MinIO object key
    file_hash       CHAR(64)     NOT NULL,          -- SHA-256 of the raw file
    uploaded_by     BIGINT       NOT NULL REFERENCES users(id),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_documents_number ON documents(document_number);

-- 3. extracted_data --------------------------------------------------
CREATE TABLE extracted_data (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id     BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    name            VARCHAR(200),
    passport_number VARCHAR(64),
    nationality     VARCHAR(64),
    date_of_birth   DATE,
    gender          VARCHAR(16),
    issue_date      DATE,
    expiry_date     DATE,
    mrz_data        TEXT,
    visual_zone     JSONB,              -- fields read from the printed/visual zone
    ocr_confidence  NUMERIC(5,4),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_extracted_document ON extracted_data(document_id);

-- 4. verification_results ------------------------------------------
CREATE TABLE verification_results (
    id                BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_id       BIGINT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ocr_status        VARCHAR(16),
    validation_status VARCHAR(16),
    tampering_score   NUMERIC(5,4),
    photo_tampering   NUMERIC(5,4),
    text_tampering    NUMERIC(5,4),
    stamp_tampering   NUMERIC(5,4),
    face_match_score  NUMERIC(5,4),
    face_match_status VARCHAR(16),
    liveness_status   VARCHAR(16),
    blacklist_status  VARCHAR(16),
    risk_score        NUMERIC(5,2),
    risk_level        VARCHAR(16),
    final_result      VARCHAR(32),
    reasons           JSONB,
    verified_by       BIGINT REFERENCES users(id),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uq_verification_document ON verification_results(document_id);

-- face embeddings for multi-identity correlation (fraud case #9) -----
CREATE TABLE face_embeddings (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    verification_id BIGINT NOT NULL REFERENCES verification_results(id) ON DELETE CASCADE,
    document_number VARCHAR(64),
    embedding       JSONB NOT NULL,          -- JSON array of floats (ArcFace 512-d)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. blacklist -----------------------------------------------------
CREATE TABLE blacklist (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    document_number VARCHAR(64),
    document_type   VARCHAR(32),
    name            VARCHAR(200),
    date_of_birth   DATE,
    reason          VARCHAR(500),
    status          VARCHAR(16) NOT NULL DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_blacklist_number ON blacklist(document_number);
CREATE INDEX idx_blacklist_name ON blacklist(name);

-- 6. audit_logs --------------------------------------------------
CREATE TABLE audit_logs (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    verification_id BIGINT REFERENCES verification_results(id) ON DELETE SET NULL,
    user_id         BIGINT REFERENCES users(id),
    action          VARCHAR(64) NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address      VARCHAR(64),
    record_hash     CHAR(64),
    blockchain_tx_id VARCHAR(128),
    integrity_status VARCHAR(16)
);
CREATE INDEX idx_audit_verification ON audit_logs(verification_id);

-- 7. notifications ---------------------------------------------
CREATE TABLE notifications (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    verification_id BIGINT REFERENCES verification_results(id) ON DELETE CASCADE,
    type            VARCHAR(32),
    recipient       VARCHAR(200),
    message         TEXT,
    status          VARCHAR(16) NOT NULL DEFAULT 'PENDING',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
