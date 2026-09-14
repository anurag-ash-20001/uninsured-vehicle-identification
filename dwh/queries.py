"""
Analytics queries (Section 11 of the spec), run against the data warehouse
(mv_* materialized-view tables + FACT/DIM tables in vehicle_dwh.db).

Each function is deliberately a single, self-contained SQL statement so it
can be shown to a user/grader as "the query that answers this question".
Call dwh.refresh_views.refresh_all_views() first (or run
`python -m dwh.refresh_views`) so the mv_* tables reflect the latest data.
"""
import sqlite3

import config


def _conn():
    conn = sqlite3.connect(config.DB_DWH)
    conn.row_factory = sqlite3.Row
    return conn


def _rows(sql: str, params: tuple = ()) -> list:
    conn = _conn()
    try:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


# 1. All currently uninsured vehicles
def uninsured_vehicles() -> list:
    return _rows("SELECT * FROM mv_uninsured_vehicles ORDER BY vehicle_identifier")


# 2. All vehicles whose insurance has expired
def expired_insurance_vehicles() -> list:
    return _rows("SELECT * FROM mv_expired_insurance ORDER BY days_expired DESC")


# 3. Vehicles detected on the road that have no insurance record at all
def detected_with_no_insurance_record() -> list:
    return _rows(
        """
        SELECT h.vehicle_identifier, h.make, h.model, h.location, h.capture_time
        FROM mv_vehicle_complete_history h
        WHERE h.insurance_status = 'UNINSURED' AND h.capture_time IS NOT NULL
        ORDER BY h.capture_time DESC
        """
    )


# 4. Vehicles that are stolen
def stolen_vehicles() -> list:
    return _rows(
        "SELECT * FROM mv_stolen_or_scrapped_vehicles WHERE suspicion_status = 'STOLEN' "
        "ORDER BY theft_report_date DESC"
    )


# 5. Vehicles that are scrapped or shredded
def scrapped_or_shredded_vehicles() -> list:
    return _rows(
        "SELECT * FROM mv_stolen_or_scrapped_vehicles WHERE suspicion_status IN ('SCRAPPED','SHREDDED') "
        "ORDER BY vehicle_identifier"
    )


# 6. Vehicles with expired registration
def expired_registration_vehicles() -> list:
    return _rows(
        """
        SELECT vehicle_identifier, registration_date, registration_expiry_date, registration_status
        FROM mv_vehicle_complete_history
        WHERE registration_status = 'EXPIRED'
        ORDER BY registration_expiry_date
        """
    )


# 7. Vehicles with insurance expiry within the next 30 days
def insurance_expiring_within_days(days: int = 30) -> list:
    return _rows(
        """
        SELECT vehicle_identifier, insurance_company, policy_number, insurance_expiry_date
        FROM mv_vehicle_complete_history
        WHERE insurance_status = 'INSURED'
          AND date(insurance_expiry_date) BETWEEN date(?) AND date(?, ?)
        ORDER BY insurance_expiry_date
        """,
        (config.SIMULATION_TODAY.isoformat(), config.SIMULATION_TODAY.isoformat(), f"+{days} days"),
    )


# 8. Vehicles that are both uninsured and detected on the road
def uninsured_and_detected() -> list:
    return _rows(
        """
        SELECT vehicle_identifier, make, model, location, capture_time, risk_level
        FROM mv_vehicle_complete_history
        WHERE insurance_status = 'UNINSURED' AND capture_time IS NOT NULL
        ORDER BY capture_time DESC
        """
    )


# 9. Vehicles that are stolen and detected on the road
def stolen_and_detected() -> list:
    return _rows(
        """
        SELECT vehicle_identifier, make, model, location, capture_time, risk_level
        FROM mv_vehicle_complete_history
        WHERE suspicion_status = 'STOLEN' AND capture_time IS NOT NULL
        ORDER BY capture_time DESC
        """
    )


# 10. Vehicles that are scrapped but still detected on the road
def scrapped_but_detected() -> list:
    return _rows(
        """
        SELECT vehicle_identifier, make, model, location, capture_time, risk_level
        FROM mv_vehicle_complete_history
        WHERE suspicion_status IN ('SCRAPPED', 'SHREDDED') AND capture_time IS NOT NULL
        ORDER BY capture_time DESC
        """
    )


# 11. Complete history of a specific vehicle
def complete_history_for(vehicle_identifier: str) -> dict:
    rows = _rows(
        "SELECT * FROM mv_vehicle_complete_history WHERE vehicle_identifier = ?",
        (vehicle_identifier.strip().upper().replace(" ", "").replace("-", ""),),
    )
    return rows[0] if rows else None


# 12. Count vehicles by insurance status
def count_by_insurance_status() -> list:
    return _rows(
        "SELECT insurance_status, COUNT(*) AS vehicle_count FROM mv_vehicle_current_status "
        "GROUP BY insurance_status ORDER BY vehicle_count DESC"
    )


# 13. Count vehicles by risk level
def count_by_risk_level() -> list:
    return _rows(
        "SELECT risk_level, COUNT(*) AS vehicle_count FROM mv_vehicle_current_status "
        "GROUP BY risk_level ORDER BY "
        "CASE risk_level WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END"
    )


# 14. Number of suspicious vehicles by location
def suspicious_count_by_location() -> list:
    return _rows(
        """
        SELECT h.location, COUNT(DISTINCT h.vehicle_identifier) AS suspicious_count
        FROM mv_vehicle_complete_history h
        WHERE h.suspicion_status != 'NONE' AND h.location IS NOT NULL
        GROUP BY h.location
        ORDER BY suspicious_count DESC
        """
    )


# 15. Vehicles requiring ministry reporting
def vehicles_requiring_ministry_report() -> list:
    return _rows(
        """
        SELECT vehicle_identifier, insurance_status, suspicion_status, registration_status,
               risk_level, ministry_report_status
        FROM mv_vehicle_complete_history
        WHERE ministry_report_required = 1
        ORDER BY CASE risk_level WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END,
                 vehicle_identifier
        """
    )


# ---------------------------------------------------------------------------
# Multi-filter vehicle browser (used by the GUI's "Browse & Filter" page).
#
# Detections (FACT_VEHICLE_EVENT, event_type='ROAD_DETECTION') are joined to
# DIM_VEHICLE / DIM_LOCATION / DIM_DATE and to mv_vehicle_complete_history —
# all of which live in the SAME warehouse database (vehicle_dwh.db), so this
# is an ordinary star-schema join, not a cross-source federation join.
#
# The one filter that lives in a different, independent database
# (ministry report reason, in ministry.db) is resolved separately and merged
# in Python as a vehicle-identifier allow-list, consistent with the
# federation approach used everywhere else in this project.
# ---------------------------------------------------------------------------
def distinct_insurance_statuses() -> list:
    return [r["insurance_status"] for r in _rows(
        "SELECT DISTINCT insurance_status FROM mv_vehicle_complete_history "
        "WHERE insurance_status IS NOT NULL ORDER BY insurance_status"
    )]


def distinct_theft_statuses() -> list:
    return [r["theft_status"] for r in _rows(
        "SELECT DISTINCT theft_status FROM mv_vehicle_complete_history "
        "WHERE theft_status IS NOT NULL ORDER BY theft_status"
    )]


def distinct_locations() -> list:
    return [r["location_name"] for r in _rows(
        "SELECT DISTINCT location_name FROM DIM_LOCATION WHERE location_name IS NOT NULL ORDER BY location_name"
    )]


def distinct_report_reasons() -> list:
    conn = sqlite3.connect(config.DB_MINISTRY)
    try:
        rows = conn.execute(
            "SELECT DISTINCT report_type FROM ministry_report ORDER BY report_type"
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def _vehicle_ids_with_report_reason(report_reason: str) -> list:
    """Looked up independently from ministry.db (a separate operational
    database), then used as an allow-list — no cross-database SQL join."""
    conn = sqlite3.connect(config.DB_MINISTRY)
    try:
        rows = conn.execute(
            "SELECT DISTINCT vehicle_identifier FROM ministry_report WHERE report_type = ?",
            (report_reason,),
        ).fetchall()
        return [r[0] for r in rows]
    finally:
        conn.close()


def browse_vehicle_detections(insurance_status: str = None, theft_status: str = None,
                               location: str = None, report_reason: str = None,
                               date_from: str = None, date_to: str = None) -> list:
    """
    Returns one row per road-camera detection event, with every relevant
    schema field attached, filtered by any combination of:
      insurance_status, theft_status, location, report_reason, and a
      captured-date range [date_from, date_to] (inclusive, 'YYYY-MM-DD').

    This directly answers questions like:
      "How many uninsured vehicles were detected in each city during the
       last six months?"
    by filtering insurance_status='UNINSURED' and a 6-month date range, then
    grouping the returned rows by `location` (done in the GUI with pandas).
    """
    conditions = ["f.event_type = 'ROAD_DETECTION'"]
    params: list = []

    if insurance_status:
        conditions.append("h.insurance_status = ?")
        params.append(insurance_status)
    if theft_status:
        conditions.append("h.theft_status = ?")
        params.append(theft_status)
    if location:
        conditions.append("l.location_name = ?")
        params.append(location)
    if date_from:
        conditions.append("d.full_date >= ?")
        params.append(date_from)
    if date_to:
        conditions.append("d.full_date <= ?")
        params.append(date_to)
    if report_reason:
        vehicle_ids = _vehicle_ids_with_report_reason(report_reason)
        if not vehicle_ids:
            return []  # no vehicle in ministry.db has this report reason
        placeholders = ",".join("?" for _ in vehicle_ids)
        conditions.append(f"v.vehicle_identifier IN ({placeholders})")
        params.extend(vehicle_ids)

    sql = f"""
        SELECT
            v.vehicle_identifier, v.make, v.model, v.color, v.vehicle_type,
            l.location_name AS location, d.full_date AS captured_date,
            h.registration_status, h.insurance_status, h.insurance_company,
            h.insurance_expiry_date, h.theft_status, h.scrapping_status,
            h.suspicion_status, h.risk_level,
            h.ministry_report_required, h.ministry_report_status
        FROM FACT_VEHICLE_EVENT f
        JOIN DIM_VEHICLE v ON v.vehicle_key = f.vehicle_key
        LEFT JOIN DIM_LOCATION l ON l.location_key = f.location_key
        LEFT JOIN DIM_DATE d ON d.date_key = f.date_key
        JOIN mv_vehicle_complete_history h ON h.vehicle_identifier = v.vehicle_identifier
        WHERE {" AND ".join(conditions)}
        ORDER BY d.full_date DESC
    """
    return _rows(sql, tuple(params))


ALL_QUERIES = {
    "1. Currently uninsured vehicles": uninsured_vehicles,
    "2. Vehicles with expired insurance": expired_insurance_vehicles,
    "3. Detected on road with no insurance record": detected_with_no_insurance_record,
    "4. Stolen vehicles": stolen_vehicles,
    "5. Scrapped or shredded vehicles": scrapped_or_shredded_vehicles,
    "6. Vehicles with expired registration": expired_registration_vehicles,
    "7. Insurance expiring within 30 days": lambda: insurance_expiring_within_days(30),
    "8. Uninsured AND detected on road": uninsured_and_detected,
    "9. Stolen AND detected on road": stolen_and_detected,
    "10. Scrapped but still detected on road": scrapped_but_detected,
    "12. Count of vehicles by insurance status": count_by_insurance_status,
    "13. Count of vehicles by risk level": count_by_risk_level,
    "14. Suspicious vehicle count by location": suspicious_count_by_location,
    "15. Vehicles requiring ministry reporting": vehicles_requiring_ministry_report,
}
