"""
SQL decomposition.

Given a single high-level user query such as:

    "Find the complete status of vehicle DL01AB1003"

this module decomposes it into the five source-specific SQL statements that
must be run against each independently-designed database, translating the
common vehicle identifier into each source's own column name.

federated_query.py is responsible for actually EXECUTING these statements;
this module only builds them, so the GUI's "Federated Query Demonstration"
page can display the decomposed SQL before/alongside execution.
"""
from dataclasses import dataclass

from mediator.identifier_mapper import normalize_identifier, SOURCE_COLUMN_MAP


@dataclass
class SourceQuery:
    source_key: str      # capture / insurance / registration / theft_scrap / ministry
    table: str
    sql: str
    params: tuple


def decompose_vehicle_query(raw_identifier: str) -> dict:
    """
    Decompose "find complete status of vehicle X" into per-source SQL.
    Returns {source_key: SourceQuery}.
    """
    vehicle_id = normalize_identifier(raw_identifier)

    queries = {}

    cap = SOURCE_COLUMN_MAP["capture"]
    queries["capture"] = SourceQuery(
        source_key="capture",
        table=cap["table"],
        sql=(
            f"SELECT capture_id, plate_number, captured_timestamp, camera_id, location, "
            f"vehicle_type, detected_make, detected_model, detected_color, confidence_score "
            f"FROM {cap['table']} WHERE {cap['id_column']} = ? ORDER BY captured_timestamp DESC"
        ),
        params=(vehicle_id,),
    )

    ins = SOURCE_COLUMN_MAP["insurance"]
    queries["insurance"] = SourceQuery(
        source_key="insurance",
        table=ins["table"],
        sql=(
            f"SELECT policy_id, registration_no, insurer_name, policy_number, "
            f"policy_start_date, policy_expiry_date, insurance_status, policy_type "
            f"FROM {ins['table']} WHERE {ins['id_column']} = ? ORDER BY policy_expiry_date DESC"
        ),
        params=(vehicle_id,),
    )

    reg = SOURCE_COLUMN_MAP["registration"]
    queries["registration"] = SourceQuery(
        source_key="registration",
        table=reg["table"],
        sql=(
            f"SELECT registration_id, vehicle_registration_id, owner_id, owner_name, "
            f"registration_date, registration_expiry_date, vehicle_make, vehicle_model, "
            f"vehicle_type, fuel_type, color, registration_status "
            f"FROM {reg['table']} WHERE {reg['id_column']} = ?"
        ),
        params=(vehicle_id,),
    )

    theft = SOURCE_COLUMN_MAP["theft_scrap"]
    queries["theft_scrap"] = SourceQuery(
        source_key="theft_scrap",
        table=theft["table"],
        sql=(
            f"SELECT record_id, vehicle_no, theft_status, theft_report_date, recovery_date, "
            f"scrapping_status, scrapping_date, shredding_date, authority_reference, remarks "
            f"FROM {theft['table']} WHERE {theft['id_column']} = ?"
        ),
        params=(vehicle_id,),
    )

    min_ = SOURCE_COLUMN_MAP["ministry"]
    queries["ministry"] = SourceQuery(
        source_key="ministry",
        table=min_["table"],
        sql=(
            f"SELECT report_id, vehicle_identifier, report_type, report_reason, detected_at, "
            f"severity, report_status, submitted_at, ministry_reference "
            f"FROM {min_['table']} WHERE {min_['id_column']} = ? ORDER BY submitted_at DESC"
        ),
        params=(vehicle_id,),
    )

    return queries
