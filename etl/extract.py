"""
ETL - EXTRACT stage.

Reads full extracts from each of the five independent operational
databases. This is the ONLY place in the ETL pipeline that touches the
source databases directly — transform.py and load.py never do.
"""
import config
import db


def _fetch_all(db_path: str, sql: str) -> list:
    conn = db.get_connection(db_path)
    try:
        cur = conn.execute(sql)
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def extract_capture() -> list:
    return _fetch_all(config.DB_CAPTURE, "SELECT * FROM vehicle_capture")


def extract_insurance() -> list:
    return _fetch_all(config.DB_INSURANCE, "SELECT * FROM insurance_policy")


def extract_registration() -> list:
    return _fetch_all(config.DB_REGISTRATION, "SELECT * FROM vehicle_registration")


def extract_theft_scrap() -> list:
    return _fetch_all(config.DB_THEFT_SCRAP, "SELECT * FROM theft_scrap_record")


def extract_ministry() -> list:
    return _fetch_all(config.DB_MINISTRY, "SELECT * FROM ministry_report")


def extract_all() -> dict:
    """Extract everything from every source in one call."""
    data = {
        "capture": extract_capture(),
        "insurance": extract_insurance(),
        "registration": extract_registration(),
        "theft_scrap": extract_theft_scrap(),
        "ministry": extract_ministry(),
    }
    print(
        "[extract] capture=%d insurance=%d registration=%d theft_scrap=%d ministry=%d"
        % (len(data["capture"]), len(data["insurance"]), len(data["registration"]),
           len(data["theft_scrap"]), len(data["ministry"]))
    )
    return data
