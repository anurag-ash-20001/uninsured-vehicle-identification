"""
Ministry of Transportation reporting API.

report_to_ministry(vehicle_identifier) determines whether a vehicle should
be reported (via the business rules + federated integration), and if so,
creates and persists a report row in ministry.db (DATABASE 5) with a unique
ministry reference. This is a simulation: no real government service is
contacted.
"""
import sqlite3
from datetime import datetime

import config
import db
from mediator.integration import get_complete_vehicle_history
from mediator.identifier_mapper import normalize_identifier
from ministry.rules import severity_for_risk_level

REASON_TEXT = {
    "UNINSURED_VEHICLE": "Vehicle detected on road with no active insurance policy on record.",
    "EXPIRED_INSURANCE": "Vehicle's insurance policy has expired.",
    "STOLEN_VEHICLE": "Vehicle is currently reported stolen.",
    "SCRAPPED_VEHICLE_DETECTED": "Vehicle marked scrapped/shredded but detected on the road.",
    "EXPIRED_REGISTRATION": "Vehicle registration has expired.",
    "MULTIPLE_SUSPICIOUS_EVENTS": "Vehicle has a prior theft/recovery history and warrants monitoring.",
}


def _next_ministry_reference(cur, vehicle_id: str) -> str:
    cur.execute("SELECT COUNT(*) AS n FROM ministry_report")
    seq = cur.fetchone()["n"] + 1
    year = config.SIMULATION_TODAY.year
    return f"MOT-{year}-{seq:06d}"


def _existing_open_report(cur, vehicle_id: str, report_type: str):
    cur.execute(
        """
        SELECT * FROM ministry_report
        WHERE vehicle_identifier = ? AND report_type = ? AND report_status != 'CLOSED'
        ORDER BY submitted_at DESC LIMIT 1
        """,
        (vehicle_id, report_type),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def report_to_ministry(raw_identifier: str, force: bool = False) -> dict:
    """
    Evaluate a vehicle and, if it meets any Section 12 reporting rule,
    create (or return the existing open) ministry report.

    Returns a dict describing the outcome:
      {"required": bool, "created": bool, "reports": [ {...row...} ], "history": {...}}
    """
    vehicle_id = normalize_identifier(raw_identifier)
    history = get_complete_vehicle_history(vehicle_id)

    if not history["ministry_report_required"] and not force:
        return {"required": False, "created": False, "reports": [], "history": history}

    reasons = history["ministry_report_reasons"] or ["MANUAL_REVIEW"]
    severity = severity_for_risk_level(history["risk_level"])
    detected_at = history["capture_time"]
    submitted_at = datetime.now().isoformat(sep=" ", timespec="seconds")

    conn = db.get_connection(config.DB_MINISTRY)
    cur = conn.cursor()

    created_reports = []
    existing_reports = []
    try:
        for reason in reasons:
            existing = _existing_open_report(cur, vehicle_id, reason)
            if existing and not force:
                existing_reports.append(existing)
                continue

            reference = _next_ministry_reference(cur, vehicle_id)
            cur.execute(
                """
                INSERT INTO ministry_report
                    (vehicle_identifier, report_type, report_reason, detected_at,
                     severity, report_status, submitted_at, ministry_reference)
                VALUES (?, ?, ?, ?, ?, 'SUBMITTED', ?, ?)
                """,
                (
                    vehicle_id, reason, REASON_TEXT.get(reason, reason), detected_at,
                    severity, submitted_at, reference,
                ),
            )
            conn.commit()
            cur.execute("SELECT * FROM ministry_report WHERE report_id = ?", (cur.lastrowid,))
            created_reports.append(dict(cur.fetchone()))
    finally:
        conn.close()

    return {
        "required": True,
        "created": len(created_reports) > 0,
        "reports": created_reports + existing_reports,
        "history": history,
    }
