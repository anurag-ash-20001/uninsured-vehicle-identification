"""
Tests for the federated query engine (querying five independent databases
and combining results) and for theft/scrap-driven suspicion + risk rules.
"""
from mediator.federated_query import execute_federated_query, execute_federated_query_with_trace
from mediator.integration import get_complete_vehicle_history


def test_federated_query_hits_all_five_sources():
    results = execute_federated_query("DL01AB1001")
    assert set(results.keys()) == {"capture", "insurance", "registration", "theft_scrap", "ministry"}
    assert len(results["capture"]) >= 1
    assert len(results["insurance"]) >= 1
    assert len(results["registration"]) == 1


def test_federated_query_trace_includes_sql_text():
    trace = execute_federated_query_with_trace("DL01AB1004")
    for source in ("capture", "insurance", "registration", "theft_scrap", "ministry"):
        assert "sql" in trace[source]
        assert "SELECT" in trace[source]["sql"].upper()
        assert "results" in trace[source]


def test_stolen_vehicle_detected_on_road_is_critical():
    h = get_complete_vehicle_history("DL01AB1004")
    assert h["suspicion_status"] == "STOLEN"
    assert h["was_captured_on_road"] is True
    assert h["risk_level"] == "CRITICAL"
    assert "STOLEN_VEHICLE" in h["ministry_report_reasons"]


def test_scrapped_vehicle_detected_on_road_is_critical():
    h = get_complete_vehicle_history("DL01AB1005")
    assert h["suspicion_status"] == "SCRAPPED"
    assert h["was_captured_on_road"] is True
    assert h["risk_level"] == "CRITICAL"
    assert "SCRAPPED_VEHICLE_DETECTED" in h["ministry_report_reasons"]


def test_shredded_vehicle():
    h = get_complete_vehicle_history("DL01AB1008")
    assert h["suspicion_status"] == "SHREDDED"
    assert h["shredding_date"] is not None
    assert h["risk_level"] == "CRITICAL"


def test_unknown_vehicle_is_handled_gracefully_without_crashing():
    h = get_complete_vehicle_history("DL99ZZ9999")
    assert h["registration_found"] is False
    assert h["insurance_status"] == "UNINSURED"
    assert h["was_captured_on_road"] is False
    assert h["sources_found"]["registration"] is False
