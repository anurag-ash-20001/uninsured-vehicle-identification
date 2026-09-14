-- ============================================================================
-- DATABASE 5: Ministry of Transportation Reporting Database (ministry.db)
-- Independently designed. Vehicle identifier attribute name: vehicle_identifier
-- ============================================================================

DROP TABLE IF EXISTS ministry_report;

CREATE TABLE ministry_report (
    report_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_identifier  TEXT NOT NULL,
    report_type         TEXT NOT NULL,       -- e.g. UNINSURED_VEHICLE, STOLEN_VEHICLE ...
    report_reason        TEXT NOT NULL,
    detected_at          TEXT,
    severity             TEXT NOT NULL,       -- LOW / MEDIUM / HIGH / CRITICAL
    report_status        TEXT NOT NULL DEFAULT 'SUBMITTED',  -- SUBMITTED / UNDER_REVIEW / CLOSED
    submitted_at          TEXT NOT NULL,
    ministry_reference    TEXT NOT NULL UNIQUE
);

CREATE INDEX idx_ministry_vehicle_identifier ON ministry_report (vehicle_identifier);
CREATE INDEX idx_ministry_report_status ON ministry_report (report_status);
CREATE INDEX idx_ministry_severity ON ministry_report (severity);
