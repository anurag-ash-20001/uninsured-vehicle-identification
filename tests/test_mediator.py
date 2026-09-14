"""
Tests for identifier mapping and SQL decomposition (mediator layer).
"""
import pytest

from mediator.identifier_mapper import normalize_identifier, id_column_for, table_for
from mediator.query_decomposer import decompose_vehicle_query


def test_normalize_identifier_strips_and_uppercases():
    assert normalize_identifier(" dl01ab1001 ") == "DL01AB1001"
    assert normalize_identifier("dl-01-ab-1001") == "DL01AB1001"


def test_normalize_identifier_rejects_empty():
    with pytest.raises(ValueError):
        normalize_identifier("   ")


def test_identifier_columns_differ_across_sources():
    # Section 3 requirement: same vehicle, deliberately different column names.
    cols = {
        id_column_for("capture"),
        id_column_for("insurance"),
        id_column_for("registration"),
        id_column_for("theft_scrap"),
        id_column_for("ministry"),
    }
    assert cols == {
        "plate_number", "registration_no", "vehicle_registration_id",
        "vehicle_no", "vehicle_identifier",
    }


def test_query_decomposition_produces_five_source_queries():
    decomposed = decompose_vehicle_query("DL01AB1003")
    assert set(decomposed.keys()) == {"capture", "insurance", "registration", "theft_scrap", "ministry"}

    assert decomposed["capture"].table == "vehicle_capture"
    assert "plate_number = ?" in decomposed["capture"].sql
    assert decomposed["capture"].params == ("DL01AB1003",)

    assert decomposed["insurance"].table == "insurance_policy"
    assert "registration_no = ?" in decomposed["insurance"].sql

    assert decomposed["registration"].table == "vehicle_registration"
    assert "vehicle_registration_id = ?" in decomposed["registration"].sql

    assert decomposed["theft_scrap"].table == "theft_scrap_record"
    assert "vehicle_no = ?" in decomposed["theft_scrap"].sql

    assert decomposed["ministry"].table == "ministry_report"
    assert "vehicle_identifier = ?" in decomposed["ministry"].sql


def test_decomposition_normalizes_raw_plate():
    decomposed = decompose_vehicle_query(" dl01ab1003 ")
    assert decomposed["capture"].params == ("DL01AB1003",)
