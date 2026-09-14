"""
One-shot project setup.

Run: python setup.py

(Re)creates all six databases from schema, seeds all five source databases
with the deterministic fictional dataset, runs the ETL pipeline to build
the data warehouse, and refreshes the materialized-view tables. After this
completes, `streamlit run app.py` and `pytest` are both ready to use.
"""
import db
from seed import seed_capture, seed_insurance, seed_registration, seed_theft_scrap, seed_ministry
from etl.pipeline import run_pipeline
from dwh.refresh_views import refresh_all_views


def main():
    print("\n[1/4] Creating database schemas...")
    db.init_all_schemas()

    print("\n[2/4] Seeding the five independent source databases...")
    seed_capture.seed()
    seed_insurance.seed()
    seed_registration.seed()
    seed_theft_scrap.seed()
    seed_ministry.seed()

    print("\n[3/4] Running ETL pipeline (extract -> transform -> load into DWH)...")
    run_pipeline()

    print("\n[4/4] Refreshing materialized-view tables...")
    refresh_all_views()

    print("\nSetup complete. Next steps:")
    print("  pytest                  # run the automated test suite")
    print("  streamlit run app.py    # launch the GUI")
    print("  python -m scripts.demo  # run the final demonstration script")


if __name__ == "__main__":
    main()
