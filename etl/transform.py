"""
ETL - TRANSFORM stage.

Takes the raw, heterogeneous extracts from the five sources and:
  * Normalizes vehicle identifiers (the same value, five different column
    names) into one conformed key.
  * Standardizes dates.
  * Resolves conflicting/duplicate column names across sources into one
    conformed vehicle attribute set (DIM_VEHICLE).
  * Detects missing values (a vehicle absent from a given source keeps
    that source's attributes as None rather than failing).
  * Produces a flat list of lifecycle "events" ready to be loaded into
    FACT_VEHICLE_EVENT, one row per meaningful thing that happened to a
    vehicle, each tagged with its originating source_system.

No database access happens here — pure Python transformation of already
extracted dicts, which makes this stage independently unit-testable.
"""
from datetime import datetime

from mediator.identifier_mapper import normalize_identifier
from ministry.rules import parse_date


def _event(vehicle_id, event_type, event_date, source_system,
           location_name=None, camera_id=None,
           status_category=None, status_value=None, event_value=None):
    return {
        "vehicle_identifier": vehicle_id,
        "event_type": event_type,
        "event_date": event_date,   # date object or None
        "location_name": location_name,
        "camera_id": camera_id,
        "status_category": status_category,
        "status_value": status_value,
        "event_value": event_value,
        "source_system": source_system,
    }


def transform(raw: dict) -> dict:
    vehicles = {}   # vehicle_id -> attribute dict (DIM_VEHICLE candidate)
    events = []

    def ensure_vehicle(vid):
        if vid not in vehicles:
            vehicles[vid] = {
                "vehicle_identifier": vid,
                "make": None, "model": None, "color": None,
                "vehicle_type": None, "fuel_type": None, "owner_name": None,
            }
        return vehicles[vid]

    # ---------------- capture ----------------
    for row in raw["capture"]:
        vid = normalize_identifier(row["plate_number"])
        v = ensure_vehicle(vid)
        v["make"] = v["make"] or row.get("detected_make")
        v["model"] = v["model"] or row.get("detected_model")
        v["color"] = v["color"] or row.get("detected_color")
        v["vehicle_type"] = v["vehicle_type"] or row.get("vehicle_type")

        event_date = parse_date(row.get("captured_timestamp"))
        events.append(_event(
            vid, "ROAD_DETECTION", event_date, "vehicle_capture.db",
            location_name=row.get("location"), camera_id=row.get("camera_id"),
            status_category="DETECTION", status_value="CAPTURED",
            event_value=f"conf={row.get('confidence_score')};plate={row.get('plate_number')}",
        ))

    # ---------------- registration ----------------
    for row in raw["registration"]:
        vid = normalize_identifier(row["vehicle_registration_id"])
        v = ensure_vehicle(vid)
        v["make"] = row.get("vehicle_make") or v["make"]
        v["model"] = row.get("vehicle_model") or v["model"]
        v["color"] = row.get("color") or v["color"]
        v["vehicle_type"] = row.get("vehicle_type") or v["vehicle_type"]
        v["fuel_type"] = row.get("fuel_type") or v["fuel_type"]
        v["owner_name"] = row.get("owner_name") or v["owner_name"]

        event_date = parse_date(row.get("registration_date"))
        events.append(_event(
            vid, "REGISTRATION", event_date, "registration.db",
            status_category="REGISTRATION", status_value=row.get("registration_status"),
            event_value=f"owner={row.get('owner_id')};expiry={row.get('registration_expiry_date')}",
        ))

    # ---------------- insurance ----------------
    for row in raw["insurance"]:
        vid = normalize_identifier(row["registration_no"])
        ensure_vehicle(vid)

        start_date = parse_date(row.get("policy_start_date"))
        expiry_date = parse_date(row.get("policy_expiry_date"))

        events.append(_event(
            vid, "INSURANCE_POLICY", start_date, "insurance.db",
            status_category="INSURANCE", status_value=row.get("insurance_status"),
            event_value=(
                f"insurer={row.get('insurer_name')};policy={row.get('policy_number')};"
                f"start={row.get('policy_start_date')};expiry={row.get('policy_expiry_date')};"
                f"type={row.get('policy_type')}"
            ),
        ))
        events.append(_event(
            vid, "INSURANCE_EXPIRY", expiry_date, "insurance.db",
            status_category="INSURANCE_LIFECYCLE", status_value="EXPIRY",
            event_value=f"policy={row.get('policy_number')}",
        ))

    # ---------------- theft / scrap ----------------
    for row in raw["theft_scrap"]:
        vid = normalize_identifier(row["vehicle_no"])
        ensure_vehicle(vid)

        theft_status = (row.get("theft_status") or "NONE").upper()
        scrapping_status = (row.get("scrapping_status") or "NONE").upper()

        if theft_status == "STOLEN" and row.get("theft_report_date"):
            events.append(_event(
                vid, "THEFT_REPORT", parse_date(row.get("theft_report_date")), "theft_scrap.db",
                status_category="THEFT", status_value="STOLEN",
                event_value=f"ref={row.get('authority_reference')}",
            ))
        if row.get("recovery_date"):
            events.append(_event(
                vid, "RECOVERY", parse_date(row.get("recovery_date")), "theft_scrap.db",
                status_category="THEFT", status_value="RECOVERED",
                event_value=f"ref={row.get('authority_reference')}",
            ))
        if theft_status == "RECOVERED" and row.get("theft_report_date") and not row.get("recovery_date"):
            events.append(_event(
                vid, "THEFT_REPORT", parse_date(row.get("theft_report_date")), "theft_scrap.db",
                status_category="THEFT", status_value="STOLEN",
                event_value=f"ref={row.get('authority_reference')}",
            ))
        if scrapping_status == "SCRAPPED" and row.get("scrapping_date"):
            events.append(_event(
                vid, "SCRAPPING", parse_date(row.get("scrapping_date")), "theft_scrap.db",
                status_category="SCRAPPING", status_value="SCRAPPED",
                event_value=f"ref={row.get('authority_reference')}",
            ))
        if row.get("shredding_date"):
            events.append(_event(
                vid, "SHREDDING", parse_date(row.get("shredding_date")), "theft_scrap.db",
                status_category="SCRAPPING", status_value="SHREDDED",
                event_value=f"ref={row.get('authority_reference')}",
            ))

    # ---------------- ministry ----------------
    for row in raw["ministry"]:
        vid = normalize_identifier(row["vehicle_identifier"])
        ensure_vehicle(vid)
        events.append(_event(
            vid, "MINISTRY_REPORT", parse_date(row.get("submitted_at")), "ministry.db",
            status_category="MINISTRY", status_value=row.get("report_type"),
            event_value=(
                f"severity={row.get('severity')};status={row.get('report_status')};"
                f"ref={row.get('ministry_reference')}"
            ),
        ))

    print(f"[transform] vehicles={len(vehicles)} events={len(events)}")
    return {"vehicles": vehicles, "events": events}
