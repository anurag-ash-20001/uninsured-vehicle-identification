"""
Integration layer.

Combines the raw, per-source result sets returned by federated_query.py
into a single logical "complete_vehicle_history" record (Section 7 of the
spec), applying the business rules in ministry/rules.py to derive
insurance_status, suspicion_status, risk_level and the ministry-reporting
decision.

This is where schema heterogeneity is resolved: each source uses different
column names and different status vocabularies; this module translates and
merges them into one conformed shape.
"""
from datetime import datetime

from mediator.federated_query import execute_federated_query
from mediator.identifier_mapper import normalize_identifier
from ministry.rules import (
    compute_insurance_status,
    compute_suspicion_status,
    compute_risk_level,
    compute_ministry_requirement,
    parse_date,
)
import config


def _latest_capture(captures: list):
    if not captures:
        return None
    def _key(c):
        d = parse_date(c.get("captured_timestamp"))
        return d or datetime.min.date()
    return max(captures, key=_key)


def get_complete_vehicle_history(raw_identifier: str, reference_datetime=None) -> dict:
    """
    Build the integrated complete_vehicle_history record for one vehicle.

    reference_datetime: the "as of" date used to evaluate insurance/registration
    validity. Defaults to the most recent road-capture timestamp for this
    vehicle if one exists, otherwise the simulation's "today".
    """
    vehicle_id = normalize_identifier(raw_identifier)
    raw = execute_federated_query(vehicle_id)

    captures = [r for r in raw.get("capture", []) if "__error__" not in r]
    policies = [r for r in raw.get("insurance", []) if "__error__" not in r]
    registrations = [r for r in raw.get("registration", []) if "__error__" not in r]
    theft_records = [r for r in raw.get("theft_scrap", []) if "__error__" not in r]
    ministry_reports = [r for r in raw.get("ministry", []) if "__error__" not in r]

    was_captured_on_road = len(captures) > 0
    latest_capture = _latest_capture(captures)
    registration = registrations[0] if registrations else None
    theft_scrap = theft_records[0] if theft_records else None

    if reference_datetime is not None:
        reference_date = reference_datetime.date() if hasattr(reference_datetime, "date") else reference_datetime
    elif latest_capture is not None:
        reference_date = parse_date(latest_capture.get("captured_timestamp")) or config.SIMULATION_TODAY
    else:
        reference_date = config.SIMULATION_TODAY

    insurance_eval = compute_insurance_status(policies, reference_date)
    insurance_status = insurance_eval["status"]
    active_policy = insurance_eval["policy"]

    suspicion_status = compute_suspicion_status(theft_scrap)

    registration_status = "UNKNOWN"
    if registration:
        registration_status = registration.get("registration_status", "UNKNOWN")
        reg_expiry = parse_date(registration.get("registration_expiry_date"))
        if reg_expiry and reg_expiry < config.SIMULATION_TODAY:
            registration_status = "EXPIRED"

    risk_level = compute_risk_level(insurance_status, suspicion_status, was_captured_on_road)

    ministry_eval = compute_ministry_requirement(
        insurance_status, suspicion_status, registration_status, was_captured_on_road
    )

    existing_report = ministry_reports[0] if ministry_reports else None

    history = {
        "vehicle_identifier": vehicle_id,
        "plate_number": vehicle_id,

        # ---- capture ----
        "capture_time": latest_capture.get("captured_timestamp") if latest_capture else None,
        "camera_id": latest_capture.get("camera_id") if latest_capture else None,
        "location": latest_capture.get("location") if latest_capture else None,
        "detection_count": len(captures),
        "was_captured_on_road": was_captured_on_road,

        # ---- vehicle attributes (prefer registration source, fallback to capture detection) ----
        "make": (registration or {}).get("vehicle_make") or (latest_capture or {}).get("detected_make"),
        "model": (registration or {}).get("vehicle_model") or (latest_capture or {}).get("detected_model"),
        "color": (registration or {}).get("color") or (latest_capture or {}).get("detected_color"),
        "vehicle_type": (registration or {}).get("vehicle_type") or (latest_capture or {}).get("vehicle_type"),
        "fuel_type": (registration or {}).get("fuel_type"),
        "owner_name": (registration or {}).get("owner_name"),
        "owner_id": (registration or {}).get("owner_id"),

        # ---- registration ----
        "registration_date": (registration or {}).get("registration_date"),
        "registration_expiry_date": (registration or {}).get("registration_expiry_date"),
        "registration_status": registration_status,
        "registration_found": registration is not None,

        # ---- insurance ----
        "insurance_company": (active_policy or {}).get("insurer_name"),
        "policy_number": (active_policy or {}).get("policy_number"),
        "insurance_start_date": (active_policy or {}).get("policy_start_date"),
        "insurance_expiry_date": (active_policy or {}).get("policy_expiry_date"),
        "insurance_status": insurance_status,
        "policy_history_count": len(policies),

        # ---- theft / scrap ----
        "theft_status": (theft_scrap or {}).get("theft_status", "NONE"),
        "theft_report_date": (theft_scrap or {}).get("theft_report_date"),
        "recovery_date": (theft_scrap or {}).get("recovery_date"),
        "scrapping_status": (theft_scrap or {}).get("scrapping_status", "NONE"),
        "scrapping_date": (theft_scrap or {}).get("scrapping_date"),
        "shredding_date": (theft_scrap or {}).get("shredding_date"),

        # ---- derived risk ----
        "suspicion_status": suspicion_status,
        "risk_level": risk_level,

        # ---- ministry ----
        "ministry_report_required": ministry_eval["required"],
        "ministry_report_reasons": ministry_eval["reasons"],
        "ministry_report_status": existing_report.get("report_status") if existing_report else None,
        "ministry_reference": existing_report.get("ministry_reference") if existing_report else None,
        "existing_ministry_reports": ministry_reports,

        # ---- raw source availability (for error-handling / transparency) ----
        "sources_found": {
            "capture": len(captures) > 0,
            "insurance": len(policies) > 0,
            "registration": registration is not None,
            "theft_scrap": theft_scrap is not None,
            "ministry": len(ministry_reports) > 0,
        },
        "evaluated_as_of": reference_date.isoformat(),
    }
    return history
