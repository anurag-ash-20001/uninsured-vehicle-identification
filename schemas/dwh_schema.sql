-- ============================================================================
-- DATA WAREHOUSE (vehicle_dwh.db) — hybrid star schema
--
-- This schema is intentionally different from the five operational schemas:
--   * Operational DBs are normalized-per-source and optimized for capturing
--     a single transaction/event with source-specific attribute names.
--   * The warehouse is denormalized around a conformed vehicle identifier,
--     uses surrogate keys, a shared DIM_DATE, and a single FACT table that
--     can answer analytical questions across all five sources at once
--     without ever touching the operational databases live.
-- ============================================================================

DROP TABLE IF EXISTS FACT_VEHICLE_EVENT;
DROP TABLE IF EXISTS DIM_VEHICLE;
DROP TABLE IF EXISTS DIM_DATE;
DROP TABLE IF EXISTS DIM_LOCATION;
DROP TABLE IF EXISTS DIM_STATUS;

-- ---------------------------------------------------------------------------
-- DIM_VEHICLE : one conformed row per real-world vehicle (SCD-1, overwrite)
-- ---------------------------------------------------------------------------
CREATE TABLE DIM_VEHICLE (
    vehicle_key         INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_identifier  TEXT NOT NULL UNIQUE,   -- conformed plate number
    make                TEXT,
    model               TEXT,
    color               TEXT,
    vehicle_type        TEXT,
    fuel_type           TEXT,
    owner_name          TEXT,
    last_updated         TEXT
);

-- ---------------------------------------------------------------------------
-- DIM_DATE : standard date dimension
-- ---------------------------------------------------------------------------
CREATE TABLE DIM_DATE (
    date_key    INTEGER PRIMARY KEY,   -- YYYYMMDD
    full_date   TEXT NOT NULL UNIQUE,
    year        INTEGER,
    month       INTEGER,
    day         INTEGER,
    quarter     INTEGER,
    month_name  TEXT
);

-- ---------------------------------------------------------------------------
-- DIM_LOCATION : road camera / detection location dimension
-- ---------------------------------------------------------------------------
CREATE TABLE DIM_LOCATION (
    location_key    INTEGER PRIMARY KEY AUTOINCREMENT,
    location_name   TEXT NOT NULL,
    camera_id       TEXT,
    UNIQUE (location_name, camera_id)
);

-- ---------------------------------------------------------------------------
-- DIM_STATUS : conformed status/event-outcome dimension
-- (category = INSURANCE / REGISTRATION / THEFT / SCRAPPING / RISK / MINISTRY)
-- ---------------------------------------------------------------------------
CREATE TABLE DIM_STATUS (
    status_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    status_category  TEXT NOT NULL,
    status_value     TEXT NOT NULL,
    UNIQUE (status_category, status_value)
);

-- ---------------------------------------------------------------------------
-- FACT_VEHICLE_EVENT : one row per significant lifecycle event
-- ---------------------------------------------------------------------------
CREATE TABLE FACT_VEHICLE_EVENT (
    event_key       INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_key     INTEGER NOT NULL REFERENCES DIM_VEHICLE(vehicle_key),
    date_key        INTEGER REFERENCES DIM_DATE(date_key),
    location_key    INTEGER REFERENCES DIM_LOCATION(location_key),
    status_key      INTEGER REFERENCES DIM_STATUS(status_key),
    event_type      TEXT NOT NULL,   -- ROAD_DETECTION / REGISTRATION / INSURANCE_POLICY /
                                       -- INSURANCE_EXPIRY / THEFT_REPORT / RECOVERY /
                                       -- SCRAPPING / SHREDDING / MINISTRY_REPORT
    event_value     TEXT,             -- free-text detail (policy no, camera reading, etc.)
    source_system   TEXT NOT NULL,    -- which operational DB the event was extracted from
    load_timestamp  TEXT NOT NULL
);

CREATE INDEX idx_fact_vehicle_key ON FACT_VEHICLE_EVENT (vehicle_key);
CREATE INDEX idx_fact_event_type ON FACT_VEHICLE_EVENT (event_type);
CREATE INDEX idx_fact_date_key ON FACT_VEHICLE_EVENT (date_key);

-- ============================================================================
-- MATERIALIZED-VIEW EQUIVALENTS
-- SQLite has no native materialized views, so these are physical summary
-- tables, fully rebuilt by dwh/refresh_views.py (python -m dwh.refresh_views).
-- ============================================================================

DROP TABLE IF EXISTS mv_vehicle_complete_history;
DROP TABLE IF EXISTS mv_vehicle_current_status;
DROP TABLE IF EXISTS mv_uninsured_vehicles;
DROP TABLE IF EXISTS mv_expired_insurance;
DROP TABLE IF EXISTS mv_stolen_or_scrapped_vehicles;

CREATE TABLE mv_vehicle_complete_history (
    vehicle_identifier          TEXT PRIMARY KEY,
    plate_number                TEXT,
    capture_time                TEXT,
    camera_id                   TEXT,
    location                    TEXT,
    make                        TEXT,
    model                       TEXT,
    color                       TEXT,
    registration_date           TEXT,
    registration_expiry_date    TEXT,
    registration_status         TEXT,
    insurance_company            TEXT,
    policy_number                TEXT,
    insurance_start_date         TEXT,
    insurance_expiry_date        TEXT,
    insurance_status              TEXT,
    theft_status                  TEXT,
    theft_report_date             TEXT,
    recovery_date                 TEXT,
    scrapping_status              TEXT,
    scrapping_date                TEXT,
    shredding_date                 TEXT,
    suspicion_status               TEXT,
    risk_level                      TEXT,
    ministry_report_required        INTEGER,
    ministry_report_status          TEXT,
    refreshed_at                     TEXT
);

CREATE TABLE mv_vehicle_current_status (
    vehicle_identifier  TEXT PRIMARY KEY,
    insurance_status    TEXT,
    registration_status TEXT,
    suspicion_status    TEXT,
    risk_level          TEXT,
    refreshed_at        TEXT
);

CREATE TABLE mv_uninsured_vehicles (
    vehicle_identifier  TEXT PRIMARY KEY,
    make                TEXT,
    model               TEXT,
    last_seen_location  TEXT,
    last_seen_time      TEXT,
    risk_level          TEXT,
    refreshed_at        TEXT
);

CREATE TABLE mv_expired_insurance (
    vehicle_identifier   TEXT PRIMARY KEY,
    insurer_name          TEXT,
    policy_number          TEXT,
    policy_expiry_date      TEXT,
    days_expired            INTEGER,
    refreshed_at             TEXT
);

CREATE TABLE mv_stolen_or_scrapped_vehicles (
    vehicle_identifier   TEXT PRIMARY KEY,
    suspicion_status      TEXT,
    theft_report_date      TEXT,
    scrapping_date          TEXT,
    shredding_date           TEXT,
    detected_on_road_after   INTEGER,   -- 1 if a capture exists after the theft/scrap event
    risk_level                TEXT,
    refreshed_at               TEXT
);
