"""
Tests for the ETL pipeline and the materialized-view refresh.
"""
import sqlite3

import config
from mediator.integration import get_complete_vehicle_history


def _dwh():
    conn = sqlite3.connect(config.DB_DWH)
    conn.row_factory = sqlite3.Row
    return conn


def test_dwh_dimensions_and_fact_are_populated():
    conn = _dwh()
    assert conn.execute("SELECT COUNT(*) FROM DIM_VEHICLE").fetchone()[0] >= 50
    assert conn.execute("SELECT COUNT(*) FROM DIM_DATE").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM DIM_LOCATION").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM DIM_STATUS").fetchone()[0] > 0
    assert conn.execute("SELECT COUNT(*) FROM FACT_VEHICLE_EVENT").fetchone()[0] >= 200
    conn.close()


def test_materialized_views_are_populated():
    conn = _dwh()
    assert conn.execute("SELECT COUNT(*) FROM mv_vehicle_complete_history").fetchone()[0] >= 50
    assert conn.execute("SELECT COUNT(*) FROM mv_uninsured_vehicles").fetchone()[0] >= 1
    assert conn.execute("SELECT COUNT(*) FROM mv_expired_insurance").fetchone()[0] >= 1
    assert conn.execute("SELECT COUNT(*) FROM mv_stolen_or_scrapped_vehicles").fetchone()[0] >= 1
    conn.close()


def test_dwh_result_matches_live_mediator_result_for_demo_vehicles():
    """The warehouse (batch) and the mediator (live) must agree, since both
    apply the exact same business rules to the exact same underlying data."""
    conn = _dwh()
    for plate in ["DL01AB1001", "DL01AB1002", "DL01AB1003", "DL01AB1004", "DL01AB1005"]:
        live = get_complete_vehicle_history(plate)
        row = conn.execute(
            "SELECT insurance_status, suspicion_status, risk_level, registration_status "
            "FROM mv_vehicle_complete_history WHERE vehicle_identifier = ?", (plate,)
        ).fetchone()
        assert row is not None
        assert row["insurance_status"] == live["insurance_status"]
        assert row["suspicion_status"] == live["suspicion_status"]
        assert row["risk_level"] == live["risk_level"]
        assert row["registration_status"] == live["registration_status"]
    conn.close()


def test_uninsured_view_only_contains_uninsured_vehicles():
    conn = _dwh()
    rows = conn.execute("SELECT vehicle_identifier FROM mv_uninsured_vehicles").fetchall()
    conn.close()
    assert len(rows) > 0
    for row in rows:
        h = get_complete_vehicle_history(row["vehicle_identifier"])
        assert h["insurance_status"] == "UNINSURED"
