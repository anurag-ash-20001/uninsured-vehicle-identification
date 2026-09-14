"""
Tests for the Ministry of Transportation reporting API.
"""
import sqlite3

import config
from ministry.reporting import report_to_ministry


def test_report_created_for_uninsured_vehicle():
    outcome = report_to_ministry("DL01AB1003")
    assert outcome["required"] is True
    assert len(outcome["reports"]) >= 1
    reasons = {r["report_type"] for r in outcome["reports"]}
    assert "UNINSURED_VEHICLE" in reasons


def test_no_report_required_for_clean_insured_vehicle():
    outcome = report_to_ministry("DL01AB1001")
    assert outcome["required"] is False
    assert outcome["created"] is False


def test_report_has_unique_ministry_reference():
    outcome = report_to_ministry("DL01AB1004")
    for r in outcome["reports"]:
        assert r["ministry_reference"].startswith("MOT-")

    conn = sqlite3.connect(config.DB_MINISTRY)
    refs = [row[0] for row in conn.execute("SELECT ministry_reference FROM ministry_report").fetchall()]
    conn.close()
    assert len(refs) == len(set(refs))  # all unique


def test_report_to_ministry_is_idempotent_for_open_reports():
    first = report_to_ministry("DL01AB1002")
    conn = sqlite3.connect(config.DB_MINISTRY)
    count_after_first = conn.execute(
        "SELECT COUNT(*) FROM ministry_report WHERE vehicle_identifier = 'DL01AB1002'"
    ).fetchone()[0]
    conn.close()

    second = report_to_ministry("DL01AB1002")
    conn = sqlite3.connect(config.DB_MINISTRY)
    count_after_second = conn.execute(
        "SELECT COUNT(*) FROM ministry_report WHERE vehicle_identifier = 'DL01AB1002'"
    ).fetchone()[0]
    conn.close()

    assert count_after_second == count_after_first  # no duplicate rows created


def test_stolen_vehicle_report_severity_is_critical():
    outcome = report_to_ministry("DL01AB1004")
    stolen_reports = [r for r in outcome["reports"] if r["report_type"] == "STOLEN_VEHICLE"]
    assert len(stolen_reports) >= 1
    assert stolen_reports[0]["severity"] == "CRITICAL"
