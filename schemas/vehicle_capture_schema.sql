-- ============================================================================
-- DATABASE 1: Vehicle Capture / Road Camera Database (vehicle_capture.db)
-- Independently designed. Vehicle identifier attribute name: plate_number
-- ============================================================================

DROP TABLE IF EXISTS vehicle_capture;

CREATE TABLE vehicle_capture (
    capture_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_number        TEXT NOT NULL,
    captured_timestamp  TEXT NOT NULL,      -- ISO-8601 datetime
    camera_id           TEXT NOT NULL,
    location             TEXT NOT NULL,
    vehicle_type        TEXT,
    detected_make       TEXT,
    detected_model      TEXT,
    detected_color      TEXT,
    confidence_score    REAL
);

CREATE INDEX idx_capture_plate_number ON vehicle_capture (plate_number);
CREATE INDEX idx_capture_timestamp ON vehicle_capture (captured_timestamp);
CREATE INDEX idx_capture_camera ON vehicle_capture (camera_id);
