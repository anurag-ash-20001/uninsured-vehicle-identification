-- ============================================================================
-- DATABASE 3: Vehicle Registration Database (registration.db)
-- Independently designed. Vehicle identifier attribute name: vehicle_registration_id
-- ============================================================================

DROP TABLE IF EXISTS vehicle_registration;

CREATE TABLE vehicle_registration (
    registration_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_registration_id   TEXT NOT NULL UNIQUE,
    owner_id                  TEXT NOT NULL,
    owner_name                TEXT NOT NULL,   -- fictional, for academic simulation only
    registration_date         TEXT NOT NULL,
    registration_expiry_date  TEXT NOT NULL,
    vehicle_make              TEXT,
    vehicle_model             TEXT,
    vehicle_type              TEXT,
    fuel_type                 TEXT,
    color                     TEXT,
    registration_status       TEXT NOT NULL    -- ACTIVE / EXPIRED / SUSPENDED (as recorded at source)
);

CREATE INDEX idx_registration_vehicle_registration_id ON vehicle_registration (vehicle_registration_id);
CREATE INDEX idx_registration_expiry_date ON vehicle_registration (registration_expiry_date);
CREATE INDEX idx_registration_status ON vehicle_registration (registration_status);
