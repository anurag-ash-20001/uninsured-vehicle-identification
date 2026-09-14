-- ============================================================================
-- DATABASE 2: Vehicle Insurance Database (insurance.db)
-- Independently designed. Vehicle identifier attribute name: registration_no
-- A vehicle may have MULTIPLE historical policy rows (policy history).
-- ============================================================================

DROP TABLE IF EXISTS insurance_policy;

CREATE TABLE insurance_policy (
    policy_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    registration_no      TEXT NOT NULL,
    insurer_name         TEXT NOT NULL,
    policy_number        TEXT NOT NULL UNIQUE,
    policy_start_date    TEXT NOT NULL,
    policy_expiry_date   TEXT NOT NULL,
    insurance_status     TEXT NOT NULL,     -- ACTIVE / EXPIRED / CANCELLED (as recorded at source)
    policy_type          TEXT
);

CREATE INDEX idx_insurance_registration_no ON insurance_policy (registration_no);
CREATE INDEX idx_insurance_expiry_date ON insurance_policy (policy_expiry_date);
CREATE INDEX idx_insurance_status ON insurance_policy (insurance_status);
