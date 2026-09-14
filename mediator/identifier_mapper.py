"""
Identifier mapping / normalization.

The five independent databases deliberately use DIFFERENT column names for
the same real-world vehicle:

    vehicle_capture.db       -> plate_number
    insurance.db              -> registration_no
    registration.db           -> vehicle_registration_id
    theft_scrap.db            -> vehicle_no
    ministry.db                -> vehicle_identifier

This module is the single place that knows that mapping, and normalizes a
raw plate string (whitespace, case, hyphens) into the canonical form used
to query every source consistently.
"""

SOURCE_COLUMN_MAP = {
    "capture": {"db_key": "capture", "table": "vehicle_capture", "id_column": "plate_number"},
    "insurance": {"db_key": "insurance", "table": "insurance_policy", "id_column": "registration_no"},
    "registration": {"db_key": "registration", "table": "vehicle_registration", "id_column": "vehicle_registration_id"},
    "theft_scrap": {"db_key": "theft_scrap", "table": "theft_scrap_record", "id_column": "vehicle_no"},
    "ministry": {"db_key": "ministry", "table": "ministry_report", "id_column": "vehicle_identifier"},
}


def normalize_identifier(raw_identifier: str) -> str:
    """Normalize a captured/typed plate number into the canonical form
    used as the join value across all independent sources."""
    if raw_identifier is None:
        raise ValueError("Vehicle identifier cannot be None")
    cleaned = raw_identifier.strip().upper().replace(" ", "").replace("-", "")
    if not cleaned:
        raise ValueError("Vehicle identifier cannot be empty")
    return cleaned


def id_column_for(source_key: str) -> str:
    """Return the vehicle-identifier column name used by a given source."""
    return SOURCE_COLUMN_MAP[source_key]["id_column"]


def table_for(source_key: str) -> str:
    return SOURCE_COLUMN_MAP[source_key]["table"]
