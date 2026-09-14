"""
Materialized-view refresh.

SQLite has no native materialized views, so mv_vehicle_complete_history,
mv_vehicle_current_status, mv_uninsured_vehicles, mv_expired_insurance and
mv_stolen_or_scrapped_vehicles are implemented as ordinary physical tables
(see schemas/dwh_schema.sql) that this module fully rebuilds on demand.

IMPORTANT: this reads ONLY from the warehouse (DIM_VEHICLE, FACT_VEHICLE_EVENT,
DIM_DATE, DIM_LOCATION, DIM_STATUS in vehicle_dwh.db) — never from the five
operational source databases — which is what makes these genuine warehouse
views rather than a re-run of the live federation. It reuses the same pure
business-rule functions (ministry/rules.py) that the mediator uses on live
lookups, so batch (warehouse) and real-time (mediator) answers agree.

Run: python -m dwh.refresh_views
"""
from datetime import datetime

import config
import db
from ministry.rules import (
    compute_insurance_status,
    compute_suspicion_status,
    compute_risk_level,
    compute_ministry_requirement,
    parse_date,
)


def _parse_kv(value: str) -> dict:
    result = {}
    if not value:
        return result
    for part in value.split(";"):
        if "=" in part:
            k, v = part.split("=", 1)
            result[k] = v
    return result


def _load_fact_rows(cur):
    cur.execute(
        """
        SELECT f.vehicle_key, v.vehicle_identifier, v.make, v.model, v.color,
               v.vehicle_type, v.fuel_type, v.owner_name,
               f.event_type, f.event_value, f.source_system,
               d.full_date, l.location_name, l.camera_id,
               s.status_category, s.status_value
        FROM FACT_VEHICLE_EVENT f
        JOIN DIM_VEHICLE v ON v.vehicle_key = f.vehicle_key
        LEFT JOIN DIM_DATE d ON d.date_key = f.date_key
        LEFT JOIN DIM_LOCATION l ON l.location_key = f.location_key
        LEFT JOIN DIM_STATUS s ON s.status_key = f.status_key
        ORDER BY v.vehicle_identifier, d.full_date
        """
    )
    return [dict(r) for r in cur.fetchall()]


def _build_vehicle_snapshots(rows: list) -> dict:
    """Group FACT rows by vehicle and reconstruct the same logical shape
    (captures / registration / insurance policies / theft_scrap / ministry
    reports) that the mediator builds directly from the operational DBs."""
    snapshots = {}

    for r in rows:
        vid = r["vehicle_identifier"]
        snap = snapshots.setdefault(vid, {
            "make": r["make"], "model": r["model"], "color": r["color"],
            "vehicle_type": r["vehicle_type"], "fuel_type": r["fuel_type"],
            "owner_name": r["owner_name"],
            "captures": [], "policies": [], "registration": None,
            "theft_report_date": None, "recovery_date": None,
            "scrapping_date": None, "shredding_date": None,
            "ministry_reports": [],
        })

        etype = r["event_type"]
        kv = _parse_kv(r["event_value"])

        if etype == "ROAD_DETECTION":
            snap["captures"].append({
                "captured_timestamp": r["full_date"],
                "location": r["location_name"],
                "camera_id": r["camera_id"],
            })
        elif etype == "REGISTRATION":
            snap["registration"] = {
                "registration_date": r["full_date"],
                "registration_expiry_date": kv.get("expiry"),
                "registration_status": r["status_value"],
                "owner_id": kv.get("owner"),
            }
        elif etype == "INSURANCE_POLICY":
            snap["policies"].append({
                "insurer_name": kv.get("insurer"),
                "policy_number": kv.get("policy"),
                "policy_start_date": kv.get("start"),
                "policy_expiry_date": kv.get("expiry"),
                "insurance_status": r["status_value"],
                "policy_type": kv.get("type"),
            })
        elif etype == "THEFT_REPORT":
            snap["theft_report_date"] = r["full_date"]
        elif etype == "RECOVERY":
            snap["recovery_date"] = r["full_date"]
        elif etype == "SCRAPPING":
            snap["scrapping_date"] = r["full_date"]
        elif etype == "SHREDDING":
            snap["shredding_date"] = r["full_date"]
        elif etype == "MINISTRY_REPORT":
            snap["ministry_reports"].append({
                "report_type": r["status_value"],
                "severity": kv.get("severity"),
                "report_status": kv.get("status"),
                "ministry_reference": kv.get("ref"),
            })

    return snapshots


def _evaluate(vid: str, snap: dict) -> dict:
    captures = snap["captures"]
    was_captured_on_road = len(captures) > 0
    latest_capture = max(captures, key=lambda c: c["captured_timestamp"] or "") if captures else None

    reference_date = (
        parse_date(latest_capture["captured_timestamp"]) if latest_capture else None
    ) or config.SIMULATION_TODAY

    insurance_eval = compute_insurance_status(snap["policies"], reference_date)
    insurance_status = insurance_eval["status"]
    active_policy = insurance_eval["policy"] or {}

    theft_scrap = {
        "theft_status": "STOLEN" if (snap["theft_report_date"] and not snap["recovery_date"])
                          else ("RECOVERED" if snap["recovery_date"] else "NONE"),
        "scrapping_status": "SCRAPPED" if (snap["scrapping_date"] or snap["shredding_date"]) else "NONE",
        "shredding_date": snap["shredding_date"],
    }
    suspicion_status = compute_suspicion_status(theft_scrap)

    registration = snap["registration"]
    registration_status = "UNKNOWN"
    if registration:
        registration_status = registration["registration_status"]
        reg_expiry = parse_date(registration.get("registration_expiry_date"))
        if reg_expiry and reg_expiry < config.SIMULATION_TODAY:
            registration_status = "EXPIRED"

    risk_level = compute_risk_level(insurance_status, suspicion_status, was_captured_on_road)
    ministry_eval = compute_ministry_requirement(
        insurance_status, suspicion_status, registration_status, was_captured_on_road
    )

    existing_ministry = snap["ministry_reports"][0] if snap["ministry_reports"] else None

    return {
        "vehicle_identifier": vid,
        "plate_number": vid,
        "capture_time": latest_capture["captured_timestamp"] if latest_capture else None,
        "camera_id": latest_capture["camera_id"] if latest_capture else None,
        "location": latest_capture["location"] if latest_capture else None,
        "make": snap["make"], "model": snap["model"], "color": snap["color"],
        "registration_date": registration["registration_date"] if registration else None,
        "registration_expiry_date": registration["registration_expiry_date"] if registration else None,
        "registration_status": registration_status,
        "insurance_company": active_policy.get("insurer_name"),
        "policy_number": active_policy.get("policy_number"),
        "insurance_start_date": active_policy.get("policy_start_date"),
        "insurance_expiry_date": active_policy.get("policy_expiry_date"),
        "insurance_status": insurance_status,
        "theft_status": theft_scrap["theft_status"],
        "theft_report_date": snap["theft_report_date"],
        "recovery_date": snap["recovery_date"],
        "scrapping_status": theft_scrap["scrapping_status"],
        "scrapping_date": snap["scrapping_date"],
        "shredding_date": snap["shredding_date"],
        "suspicion_status": suspicion_status,
        "risk_level": risk_level,
        "ministry_report_required": 1 if ministry_eval["required"] else 0,
        "ministry_report_status": existing_ministry["report_status"] if existing_ministry else None,
        "was_captured_on_road": was_captured_on_road,
    }


def refresh_all_views() -> dict:
    conn = db.get_connection(config.DB_DWH)
    cur = conn.cursor()

    rows = _load_fact_rows(cur)
    snapshots = _build_vehicle_snapshots(rows)

    now = datetime.now().isoformat(sep=" ", timespec="seconds")

    cur.execute("DELETE FROM mv_vehicle_complete_history")
    cur.execute("DELETE FROM mv_vehicle_current_status")
    cur.execute("DELETE FROM mv_uninsured_vehicles")
    cur.execute("DELETE FROM mv_expired_insurance")
    cur.execute("DELETE FROM mv_stolen_or_scrapped_vehicles")

    counts = {"complete_history": 0, "current_status": 0, "uninsured": 0,
              "expired_insurance": 0, "stolen_or_scrapped": 0}

    for vid, snap in snapshots.items():
        ev = _evaluate(vid, snap)

        cur.execute(
            """
            INSERT INTO mv_vehicle_complete_history
                (vehicle_identifier, plate_number, capture_time, camera_id, location,
                 make, model, color, registration_date, registration_expiry_date,
                 registration_status, insurance_company, policy_number,
                 insurance_start_date, insurance_expiry_date, insurance_status,
                 theft_status, theft_report_date, recovery_date, scrapping_status,
                 scrapping_date, shredding_date, suspicion_status, risk_level,
                 ministry_report_required, ministry_report_status, refreshed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ev["vehicle_identifier"], ev["plate_number"], ev["capture_time"], ev["camera_id"],
                ev["location"], ev["make"], ev["model"], ev["color"], ev["registration_date"],
                ev["registration_expiry_date"], ev["registration_status"], ev["insurance_company"],
                ev["policy_number"], ev["insurance_start_date"], ev["insurance_expiry_date"],
                ev["insurance_status"], ev["theft_status"], ev["theft_report_date"],
                ev["recovery_date"], ev["scrapping_status"], ev["scrapping_date"], ev["shredding_date"],
                ev["suspicion_status"], ev["risk_level"], ev["ministry_report_required"],
                ev["ministry_report_status"], now,
            ),
        )
        counts["complete_history"] += 1

        cur.execute(
            """
            INSERT INTO mv_vehicle_current_status
                (vehicle_identifier, insurance_status, registration_status,
                 suspicion_status, risk_level, refreshed_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (vid, ev["insurance_status"], ev["registration_status"], ev["suspicion_status"],
             ev["risk_level"], now),
        )
        counts["current_status"] += 1

        if ev["insurance_status"] == "UNINSURED":
            cur.execute(
                """
                INSERT INTO mv_uninsured_vehicles
                    (vehicle_identifier, make, model, last_seen_location, last_seen_time,
                     risk_level, refreshed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (vid, ev["make"], ev["model"], ev["location"], ev["capture_time"],
                 ev["risk_level"], now),
            )
            counts["uninsured"] += 1

        if ev["insurance_status"] == "EXPIRED":
            days_expired = None
            expiry = parse_date(ev["insurance_expiry_date"])
            if expiry:
                days_expired = (config.SIMULATION_TODAY - expiry).days
            cur.execute(
                """
                INSERT INTO mv_expired_insurance
                    (vehicle_identifier, insurer_name, policy_number, policy_expiry_date,
                     days_expired, refreshed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (vid, ev["insurance_company"], ev["policy_number"], ev["insurance_expiry_date"],
                 days_expired, now),
            )
            counts["expired_insurance"] += 1

        if ev["suspicion_status"] in ("STOLEN", "SCRAPPED", "SHREDDED"):
            cur.execute(
                """
                INSERT INTO mv_stolen_or_scrapped_vehicles
                    (vehicle_identifier, suspicion_status, theft_report_date, scrapping_date,
                     shredding_date, detected_on_road_after, risk_level, refreshed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (vid, ev["suspicion_status"], ev["theft_report_date"], ev["scrapping_date"],
                 ev["shredding_date"], 1 if ev["was_captured_on_road"] else 0, ev["risk_level"], now),
            )
            counts["stolen_or_scrapped"] += 1

    conn.commit()
    conn.close()

    print("[refresh_views] rebuilt materialized-view tables:", counts)
    return counts


if __name__ == "__main__":
    refresh_all_views()
