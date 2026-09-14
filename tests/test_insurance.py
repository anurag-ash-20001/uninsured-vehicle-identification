"""
Tests for insurance / registration business-rule evaluation via the
mediator's integrated complete_vehicle_history, using the fixed
demonstration vehicles DL01AB1001-1010.
"""
from mediator.integration import get_complete_vehicle_history


def test_valid_insured_vehicle():
    h = get_complete_vehicle_history("DL01AB1001")
    assert h["insurance_status"] == "INSURED"
    assert h["risk_level"] == "LOW"
    assert h["ministry_report_required"] is False


def test_expired_insurance_vehicle():
    h = get_complete_vehicle_history("DL01AB1002")
    assert h["insurance_status"] == "EXPIRED"
    assert "EXPIRED_INSURANCE" in h["ministry_report_reasons"]
    assert h["ministry_report_required"] is True


def test_missing_insurance_vehicle():
    h = get_complete_vehicle_history("DL01AB1003")
    assert h["insurance_status"] == "UNINSURED"
    assert h["policy_history_count"] == 0
    assert "UNINSURED_VEHICLE" in h["ministry_report_reasons"]


def test_expired_registration_vehicle():
    h = get_complete_vehicle_history("DL01AB1006")
    assert h["registration_status"] == "EXPIRED"
    assert "EXPIRED_REGISTRATION" in h["ministry_report_reasons"]


def test_multi_policy_vehicle_uses_currently_active_policy():
    h = get_complete_vehicle_history("DL01AB1010")
    assert h["policy_history_count"] >= 2
    assert h["insurance_status"] == "INSURED"


def test_uninsured_and_detected_on_road_is_high_risk():
    h = get_complete_vehicle_history("DL01AB1003")
    assert h["was_captured_on_road"] is True
    assert h["risk_level"] == "HIGH"
