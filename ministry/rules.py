"""
Business rules (Section 12 of the spec).

Pure functions only — no database access here. They take already-fetched,
already-normalized values (as produced by the federated query) and derive
insurance status, suspicion status, risk level, and the ministry-reporting
decision. Keeping these as pure functions means they are independently
unit-testable and reusable from both the mediator (live lookups) and the
ETL (batch warehouse loads).
"""
from datetime import date, datetime


def parse_date(value):
    """Accepts 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS' (or a date/datetime
    already) and returns a date object. Returns None for missing/invalid input."""
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    text = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# RULE 1 / RULE 2 / RULE 3 — insurance status
# ---------------------------------------------------------------------------
def compute_insurance_status(policies: list, reference_date: date) -> dict:
    """
    policies: list of dicts with policy_start_date, policy_expiry_date,
              insurance_status (source-recorded), insurer_name, policy_number.
    reference_date: the date/time of capture (or "now" for a live lookup).

    Returns {"status": "INSURED"|"EXPIRED"|"UNINSURED", "policy": dict|None}
    """
    if not policies:
        return {"status": "UNINSURED", "policy": None}

    valid_candidates = []
    expired_candidates = []

    for p in policies:
        if str(p.get("insurance_status", "")).upper() == "CANCELLED":
            continue
        start = parse_date(p.get("policy_start_date"))
        expiry = parse_date(p.get("policy_expiry_date"))
        if start is None or expiry is None:
            continue
        if start <= reference_date <= expiry:
            valid_candidates.append(p)
        elif expiry < reference_date:
            expired_candidates.append(p)

    if valid_candidates:
        # if multiple somehow overlap, prefer the one with the latest expiry
        best = max(valid_candidates, key=lambda p: parse_date(p.get("policy_expiry_date")))
        return {"status": "INSURED", "policy": best}

    if expired_candidates:
        most_recent = max(expired_candidates, key=lambda p: parse_date(p.get("policy_expiry_date")))
        return {"status": "EXPIRED", "policy": most_recent}

    # policies exist only as future-dated / unparsable -> treat as uninsured today
    return {"status": "UNINSURED", "policy": None}


# ---------------------------------------------------------------------------
# RULE 4 / RULE 5 — suspicion status
# ---------------------------------------------------------------------------
def compute_suspicion_status(theft_scrap: dict) -> str:
    """
    theft_scrap: dict with theft_status, scrapping_status, shredding_date (or None).
    Returns one of: NONE, STOLEN, SCRAPPED, SHREDDED, RECOVERED_HISTORY
    """
    if not theft_scrap:
        return "NONE"

    theft_status = str(theft_scrap.get("theft_status") or "NONE").upper()
    scrapping_status = str(theft_scrap.get("scrapping_status") or "NONE").upper()
    shredding_date = theft_scrap.get("shredding_date")

    if shredding_date:
        return "SHREDDED"
    if scrapping_status == "SCRAPPED":
        return "SCRAPPED"
    if theft_status == "STOLEN":
        return "STOLEN"
    if theft_status == "RECOVERED":
        return "RECOVERED_HISTORY"
    return "NONE"


# ---------------------------------------------------------------------------
# RULE 6 / RULE 7 / RULE 8 / RULE 9 — risk level
# ---------------------------------------------------------------------------
def compute_risk_level(insurance_status: str, suspicion_status: str, was_captured_on_road: bool) -> str:
    if suspicion_status == "STOLEN" and was_captured_on_road:
        return "CRITICAL"                                   # RULE 6
    if suspicion_status in ("SCRAPPED", "SHREDDED") and was_captured_on_road:
        return "CRITICAL"                                   # RULE 9
    if insurance_status == "UNINSURED" and was_captured_on_road:
        return "HIGH"                                        # RULE 7
    if insurance_status == "EXPIRED" and was_captured_on_road:
        return "HIGH"                                        # RULE 8
    if suspicion_status == "STOLEN":
        return "HIGH"
    if suspicion_status in ("SCRAPPED", "SHREDDED"):
        return "MEDIUM"
    if suspicion_status == "RECOVERED_HISTORY":
        return "MEDIUM"
    if insurance_status in ("UNINSURED", "EXPIRED"):
        return "MEDIUM"
    return "LOW"


# ---------------------------------------------------------------------------
# RULE 10 — ministry reporting requirement
# ---------------------------------------------------------------------------
REPORT_REASON_UNINSURED = "UNINSURED_VEHICLE"
REPORT_REASON_EXPIRED_INSURANCE = "EXPIRED_INSURANCE"
REPORT_REASON_STOLEN = "STOLEN_VEHICLE"
REPORT_REASON_SCRAPPED_DETECTED = "SCRAPPED_VEHICLE_DETECTED"
REPORT_REASON_EXPIRED_REGISTRATION = "EXPIRED_REGISTRATION"
REPORT_REASON_SUSPICIOUS = "MULTIPLE_SUSPICIOUS_EVENTS"


def compute_ministry_requirement(insurance_status: str, suspicion_status: str,
                                  registration_status: str, was_captured_on_road: bool) -> dict:
    reasons = []

    if insurance_status == "UNINSURED":
        reasons.append(REPORT_REASON_UNINSURED)
    if insurance_status == "EXPIRED":
        reasons.append(REPORT_REASON_EXPIRED_INSURANCE)
    if suspicion_status == "STOLEN":
        reasons.append(REPORT_REASON_STOLEN)
    if suspicion_status in ("SCRAPPED", "SHREDDED") and was_captured_on_road:
        reasons.append(REPORT_REASON_SCRAPPED_DETECTED)
    if registration_status == "EXPIRED":
        reasons.append(REPORT_REASON_EXPIRED_REGISTRATION)
    if suspicion_status == "RECOVERED_HISTORY" and insurance_status == "INSURED":
        reasons.append(REPORT_REASON_SUSPICIOUS)

    return {"required": len(reasons) > 0, "reasons": reasons}


def severity_for_risk_level(risk_level: str) -> str:
    return {"CRITICAL": "CRITICAL", "HIGH": "HIGH", "MEDIUM": "MEDIUM", "LOW": "LOW"}.get(risk_level, "LOW")
