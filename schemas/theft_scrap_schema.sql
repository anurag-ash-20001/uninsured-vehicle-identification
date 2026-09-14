-- ============================================================================
-- DATABASE 4: Vehicle Theft and Scrapping Database (theft_scrap.db)
-- Independently designed. Vehicle identifier attribute name: vehicle_no
-- ============================================================================

DROP TABLE IF EXISTS theft_scrap_record;

CREATE TABLE theft_scrap_record (
    record_id           INTEGER PRIMARY KEY AUTOINCREMENT,
    vehicle_no          TEXT NOT NULL,
    theft_status        TEXT NOT NULL DEFAULT 'NONE',      -- NONE / STOLEN / RECOVERED
    theft_report_date   TEXT,
    recovery_date       TEXT,
    scrapping_status    TEXT NOT NULL DEFAULT 'NONE',      -- NONE / SCRAPPED
    scrapping_date      TEXT,
    shredding_date      TEXT,
    authority_reference TEXT,
    remarks              TEXT
);

CREATE INDEX idx_theft_scrap_vehicle_no ON theft_scrap_record (vehicle_no);
CREATE INDEX idx_theft_scrap_theft_status ON theft_scrap_record (theft_status);
CREATE INDEX idx_theft_scrap_scrapping_status ON theft_scrap_record (scrapping_status);
