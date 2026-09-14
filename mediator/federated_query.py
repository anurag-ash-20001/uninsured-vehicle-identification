"""
Federated query execution.

Executes the decomposed, source-specific SQL statements (built by
query_decomposer.py) against each of the five INDEPENDENT SQLite databases
and returns the raw, per-source result sets. No cross-database SQL JOIN is
ever performed — each source is queried locally and results are combined
in Python, which is the defining characteristic of query federation /
mediation over autonomous, heterogeneous sources.
"""
import sqlite3

import config
from mediator.query_decomposer import decompose_vehicle_query

SOURCE_DB_PATHS = {
    "capture": config.DB_CAPTURE,
    "insurance": config.DB_INSURANCE,
    "registration": config.DB_REGISTRATION,
    "theft_scrap": config.DB_THEFT_SCRAP,
    "ministry": config.DB_MINISTRY,
}


def _run_local_query(db_path: str, sql: str, params: tuple) -> list:
    """Execute one query against one autonomous source database.
    Gracefully returns [] if the source database/table is unavailable,
    so a single unreachable source never crashes the whole federation."""
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.execute(sql, params)
            rows = [dict(r) for r in cur.fetchall()]
            return rows
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return [{"__error__": f"source unavailable: {exc}"}]


def execute_federated_query(raw_identifier: str) -> dict:
    """
    Run the full 5-way federated query for one vehicle identifier.
    Returns {source_key: [rows...]} — raw, untranslated results.
    """
    decomposed = decompose_vehicle_query(raw_identifier)
    results = {}
    for source_key, source_query in decomposed.items():
        db_path = SOURCE_DB_PATHS[source_key]
        results[source_key] = _run_local_query(db_path, source_query.sql, source_query.params)
    return results


def execute_federated_query_with_trace(raw_identifier: str) -> dict:
    """
    Same as execute_federated_query, but also returns the exact SQL text
    sent to each source (for the GUI's federation-demonstration page).
    Returns {source_key: {"sql": str, "params": tuple, "results": [rows]}}
    """
    decomposed = decompose_vehicle_query(raw_identifier)
    trace = {}
    for source_key, source_query in decomposed.items():
        db_path = SOURCE_DB_PATHS[source_key]
        rows = _run_local_query(db_path, source_query.sql, source_query.params)
        trace[source_key] = {
            "table": source_query.table,
            "sql": source_query.sql,
            "params": source_query.params,
            "results": rows,
        }
    return trace


def fetch_all_known_vehicle_identifiers() -> set:
    """
    Union of every vehicle identifier seen across all five independent
    sources. Used by the ETL and the materialized-view refresh so the
    warehouse covers vehicles even if they are missing from some sources.
    """
    ids = set()

    queries = [
        (config.DB_CAPTURE, "SELECT DISTINCT plate_number AS vid FROM vehicle_capture"),
        (config.DB_INSURANCE, "SELECT DISTINCT registration_no AS vid FROM insurance_policy"),
        (config.DB_REGISTRATION, "SELECT DISTINCT vehicle_registration_id AS vid FROM vehicle_registration"),
        (config.DB_THEFT_SCRAP, "SELECT DISTINCT vehicle_no AS vid FROM theft_scrap_record"),
        (config.DB_MINISTRY, "SELECT DISTINCT vehicle_identifier AS vid FROM ministry_report"),
    ]
    for db_path, sql in queries:
        for row in _run_local_query(db_path, sql, ()):
            if "vid" in row and row["vid"]:
                ids.add(row["vid"])
    return ids
