"""
Tests for the multi-filter vehicle browser used by the GUI's
"Browse & Filter" page (dwh/queries.py::browse_vehicle_detections and its
supporting distinct_*() lookups).
"""
from datetime import timedelta

import config
import dwh.queries as q


def test_distinct_lookups_return_expected_vocabulary():
    assert set(q.distinct_insurance_statuses()) <= {"INSURED", "EXPIRED", "UNINSURED"}
    assert set(q.distinct_theft_statuses()) <= {"NONE", "STOLEN", "RECOVERED"}
    assert len(q.distinct_locations()) >= 1
    reasons = set(q.distinct_report_reasons())
    assert reasons <= {
        "UNINSURED_VEHICLE", "EXPIRED_INSURANCE", "STOLEN_VEHICLE",
        "SCRAPPED_VEHICLE_DETECTED", "EXPIRED_REGISTRATION", "MULTIPLE_SUSPICIOUS_EVENTS",
    }
    assert len(reasons) > 0


def test_browse_filters_by_insurance_status():
    rows = q.browse_vehicle_detections(insurance_status="UNINSURED")
    assert len(rows) > 0
    assert all(r["insurance_status"] == "UNINSURED" for r in rows)


def test_browse_filters_by_theft_status():
    rows = q.browse_vehicle_detections(theft_status="STOLEN")
    assert len(rows) > 0
    assert all(r["theft_status"] == "STOLEN" for r in rows)


def test_browse_filters_by_report_reason_matches_ministry_db():
    rows = q.browse_vehicle_detections(report_reason="STOLEN_VEHICLE")
    assert len(rows) > 0
    vehicle_ids = {r["vehicle_identifier"] for r in rows}
    assert "DL01AB1004" in vehicle_ids  # the fixed stolen demo vehicle


def test_browse_filters_by_date_range_last_six_months():
    date_from = (config.SIMULATION_TODAY - timedelta(days=180)).isoformat()
    date_to = config.SIMULATION_TODAY.isoformat()
    rows = q.browse_vehicle_detections(date_from=date_from, date_to=date_to)
    assert len(rows) > 0
    for r in rows:
        assert date_from <= r["captured_date"] <= date_to


def test_browse_filters_by_location():
    locations = q.distinct_locations()
    rows = q.browse_vehicle_detections(location=locations[0])
    assert len(rows) > 0
    assert all(r["location"] == locations[0] for r in rows)


def test_browse_combined_filters_answers_uninsured_by_city_question():
    """'How many uninsured vehicles were detected in each city during the
    last six months?' — the exact scenario the Browse & Filter page targets."""
    date_from = (config.SIMULATION_TODAY - timedelta(days=180)).isoformat()
    date_to = config.SIMULATION_TODAY.isoformat()
    rows = q.browse_vehicle_detections(insurance_status="UNINSURED", date_from=date_from, date_to=date_to)
    assert len(rows) > 0

    by_city = {}
    for r in rows:
        by_city.setdefault(r["location"], set()).add(r["vehicle_identifier"])
    assert len(by_city) > 1  # spread across more than one city
    for city, vehicles in by_city.items():
        assert len(vehicles) > 0


def test_browse_with_no_matches_returns_empty_list():
    rows = q.browse_vehicle_detections(report_reason="NOT_A_REAL_REASON")
    assert rows == []
