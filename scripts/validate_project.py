"""
Final validation script (Section 23).

Runs every checklist item end-to-end against the live project and prints a
PASS/FAIL report. Run this AFTER `python setup.py`.

Run: python -m scripts.validate_project
"""
import os
import sqlite3

import config
from mediator.federated_query import execute_federated_query
from mediator.integration import get_complete_vehicle_history
from mediator.query_decomposer import decompose_vehicle_query
from ministry.reporting import report_to_ministry

RESULTS = []


def check(description, fn):
    try:
        ok, detail = fn()
    except Exception as exc:  # noqa: BLE001 - validation script must never crash mid-report
        ok, detail = False, f"EXCEPTION: {exc}"
    RESULTS.append((description, ok, detail))


def _count(db_path, table):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def main():
    # 1. All databases are created
    check("1. All six databases exist on disk", lambda: (
        all(os.path.exists(p) for p in [
            config.DB_CAPTURE, config.DB_INSURANCE, config.DB_REGISTRATION,
            config.DB_THEFT_SCRAP, config.DB_MINISTRY, config.DB_DWH,
        ]), "checked file existence"
    ))

    # 2. All tables are created
    check("2. All required tables exist", lambda: (
        all([
            _count(config.DB_CAPTURE, "vehicle_capture") >= 0,
            _count(config.DB_INSURANCE, "insurance_policy") >= 0,
            _count(config.DB_REGISTRATION, "vehicle_registration") >= 0,
            _count(config.DB_THEFT_SCRAP, "theft_scrap_record") >= 0,
            _count(config.DB_MINISTRY, "ministry_report") >= 0,
            _count(config.DB_DWH, "DIM_VEHICLE") >= 0,
            _count(config.DB_DWH, "FACT_VEHICLE_EVENT") >= 0,
        ]), "checked table existence via COUNT(*)"
    ))

    # 3. All databases contain data
    def _has_data():
        counts = {
            "capture": _count(config.DB_CAPTURE, "vehicle_capture"),
            "insurance": _count(config.DB_INSURANCE, "insurance_policy"),
            "registration": _count(config.DB_REGISTRATION, "vehicle_registration"),
            "theft_scrap": _count(config.DB_THEFT_SCRAP, "theft_scrap_record"),
            "ministry": _count(config.DB_MINISTRY, "ministry_report"),
        }
        ok = (counts["capture"] >= 50 and counts["insurance"] >= 50 and
              counts["registration"] >= 50 and counts["theft_scrap"] >= 30 and
              counts["ministry"] >= 20)
        return ok, str(counts)
    check("3. All databases contain sufficient data (Section 4 minimums)", _has_data)

    # 4. Common vehicle identifiers correctly map between databases
    def _mapping():
        h = get_complete_vehicle_history("DL01AB1001")
        ok = h["sources_found"]["capture"] and h["sources_found"]["insurance"] and h["sources_found"]["registration"]
        return ok, f"sources_found={h['sources_found']}"
    check("4. Common vehicle identifier maps correctly across sources", _mapping)

    # 5. At least one vehicle exists in all five sources
    def _all_five():
        h = get_complete_vehicle_history("DL01AB1004")  # stolen + reported vehicle
        ok = all(h["sources_found"].values())
        return ok, f"DL01AB1004 sources_found={h['sources_found']}"
    check("5. At least one vehicle exists in all five sources", _all_five)

    # 6. At least one vehicle has no insurance
    check("6. At least one vehicle has no insurance", lambda: (
        get_complete_vehicle_history("DL01AB1003")["insurance_status"] == "UNINSURED", "DL01AB1003"
    ))

    # 7. At least one vehicle has expired insurance
    check("7. At least one vehicle has expired insurance", lambda: (
        get_complete_vehicle_history("DL01AB1002")["insurance_status"] == "EXPIRED", "DL01AB1002"
    ))

    # 8. At least one vehicle is stolen
    check("8. At least one vehicle is stolen", lambda: (
        get_complete_vehicle_history("DL01AB1004")["suspicion_status"] == "STOLEN", "DL01AB1004"
    ))

    # 9. At least one vehicle is scrapped
    check("9. At least one vehicle is scrapped", lambda: (
        get_complete_vehicle_history("DL01AB1005")["suspicion_status"] == "SCRAPPED", "DL01AB1005"
    ))

    # 10. At least one vehicle detected while uninsured
    check("10. At least one vehicle detected on road while uninsured", lambda: (
        (lambda h: (h["was_captured_on_road"] and h["insurance_status"] == "UNINSURED"))(
            get_complete_vehicle_history("DL01AB1003")
        ), "DL01AB1003"
    ))

    # 11. Federated query works
    check("11. Federated query executes across all 5 sources", lambda: (
        set(execute_federated_query("DL01AB1001").keys()) ==
        {"capture", "insurance", "registration", "theft_scrap", "ministry"}, "keys matched"
    ))

    # 12. SQL decomposition works
    check("12. SQL decomposition produces 5 distinct source queries", lambda: (
        len(decompose_vehicle_query("DL01AB1001")) == 5, "5 SourceQuery objects returned"
    ))

    # 13. ETL works / 14. DWH is populated
    def _dwh_populated():
        dim_v = _count(config.DB_DWH, "DIM_VEHICLE")
        fact = _count(config.DB_DWH, "FACT_VEHICLE_EVENT")
        return (dim_v >= 50 and fact > 0), f"DIM_VEHICLE={dim_v} FACT_VEHICLE_EVENT={fact}"
    check("13/14. ETL ran and DWH (DIM/FACT) is populated", _dwh_populated)

    # 15. Materialized-view tables refresh
    def _mv_populated():
        mv = _count(config.DB_DWH, "mv_vehicle_complete_history")
        return mv >= 50, f"mv_vehicle_complete_history={mv}"
    check("15. Materialized-view tables are populated", _mv_populated)

    # 16. Ministry reporting works
    def _ministry_works():
        outcome = report_to_ministry("DL01AB1003")
        return outcome["required"] and len(outcome["reports"]) >= 1, str(outcome["reports"][:1])
    check("16. Ministry reporting API works end-to-end", _ministry_works)

    # 17. GUI exists (importable / file present) — actual browser run is manual
    check("17. GUI entry point (app.py) exists", lambda: (
        os.path.exists(os.path.join(config.BASE_DIR, "app.py")), "app.py present"
    ))

    # 18. Tests exist
    check("18. Automated test suite exists", lambda: (
        len([f for f in os.listdir(os.path.join(config.BASE_DIR, "tests")) if f.startswith("test_")]) >= 5,
        "5 test_*.py files expected"
    ))

    # 19. README exists and is substantial
    check("19. README.md exists and is complete", lambda: (
        os.path.exists(os.path.join(config.BASE_DIR, "README.md")) and
        os.path.getsize(os.path.join(config.BASE_DIR, "README.md")) > 3000,
        "README.md present and non-trivial"
    ))

    print("=" * 90)
    print("FINAL VALIDATION REPORT")
    print("=" * 90)
    passed = 0
    for desc, ok, detail in RESULTS:
        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        print(f"[{status}] {desc}\n         -> {detail}")
    print("-" * 90)
    print(f"{passed}/{len(RESULTS)} checks passed")
    print("=" * 90)
    return passed == len(RESULTS)


if __name__ == "__main__":
    all_passed = main()
    raise SystemExit(0 if all_passed else 1)
