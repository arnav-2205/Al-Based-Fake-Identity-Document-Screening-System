-- SIH26188 — seed data for the demo.
-- BCrypt hashes below are for the passwords documented in README.md (strength 10).

INSERT INTO users (officer_id, name, email, password_hash, role, checkpoint_id) VALUES
 ('admin',          'System Administrator', 'admin@ssb.gov.in',        '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'ADMIN',        'HQ'),
 ('officer1',       'Officer R. Sharma',    'officer1@ssb.gov.in',     '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'OFFICER',      'ICP-ATTARI'),
 ('investigator1',  'Investigator P. Nair', 'investigator1@ssb.gov.in','$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'INVESTIGATOR', 'HQ'),
 ('auditor1',       'Auditor S. Rao',       'auditor1@ssb.gov.in',     '$2a$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy', 'AUDITOR',      'HQ');
-- NOTE: the hash above corresponds to the string "password". The backend also
-- exposes POST /api/auth/dev/reset-passwords (ADMIN, non-prod) to set the
-- README credentials. For a zero-config demo, log in with password = "password".

INSERT INTO blacklist (document_number, document_type, name, date_of_birth, reason, status) VALUES
 ('P1234567',  'PASSPORT', 'John Fictitious',  '1985-04-12', 'INTERPOL red notice — identity fraud', 'ACTIVE'),
 ('X9988776',  'PASSPORT', 'Anon Suspect',     '1990-11-02', 'Watchlist — multiple forged entries',  'ACTIVE'),
 ('V0001111',  'VISA',     'Test Forged Visa', '1978-01-30', 'Known counterfeit visa serial batch',  'ACTIVE');
