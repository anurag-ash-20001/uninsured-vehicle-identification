"""
Final demonstration script (Section 23).

For each headline demonstration vehicle (DL01AB1001 - DL01AB1010), runs the
full federated query + mediator integration and prints the resulting
complete_vehicle_history, showing SQL decomposition, federation, and the
business rules engine working end-to-end on the live source databases.

Run: python -m scripts.demo
"""
from mediator.query_decomposer import decompose_vehicle_query
from mediator.federated_query import execute_federated_query
from mediator.integration import get_complete_vehicle_history

DEMO_VEHICLES = [
    ("DL01AB1001", "valid insurance"),
    ("DL01AB1002", "expired insurance"),
    ("DL01AB1003", "no insurance"),
    ("DL01AB1004", "stolen"),
    ("DL01AB1005", "scrapped"),
    ("DL01AB1006", "expired registration"),
    ("DL01AB1007", "valid insurance but suspicious/theft history"),
    ("DL01AB1008", "shredded"),
    ("DL01AB1009", "recovered stolen vehicle"),
    ("DL01AB1010", "multiple historical insurance policies"),
]


def show_decomposition(plate: str):
    print(f"\n  SQL decomposition for '{plate}':")
    decomposed = decompose_vehicle_query(plate)
    for source_key, sq in decomposed.items():
        print(f"    [{source_key}] {sq.sql}  params={sq.params}")


def show_federation(plate: str):
    raw = execute_federated_query(plate)
    print(f"\n  Federated raw result counts: "
          f"capture={len(raw['capture'])} insurance={len(raw['insurance'])} "
          f"registration={len(raw['registration'])} theft_scrap={len(raw['theft_scrap'])} "
          f"ministry={len(raw['ministry'])}")


def main():
    print("=" * 90)
    print("FINAL DEMONSTRATION — Identification of Uninsured Vehicles While They Are on Road")
    print("=" * 90)

    for plate, expectation in DEMO_VEHICLES:
        print("\n" + "-" * 90)
        print(f"VEHICLE {plate}  (expected category: {expectation})")
        print("-" * 90)

        show_decomposition(plate)
        show_federation(plate)

        history = get_complete_vehicle_history(plate)
        print("\n  Integrated complete_vehicle_history:")
        for k in [
            "make", "model", "color", "registration_status", "insurance_status",
            "theft_status", "scrapping_status", "suspicion_status", "risk_level",
            "ministry_report_required", "ministry_report_reasons",
        ]:
            print(f"    {k:28s}: {history[k]}")

    print("\n" + "=" * 90)
    print("DEMONSTRATION COMPLETE")
    print("=" * 90)


if __name__ == "__main__":
    main()
