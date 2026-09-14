"""
ETL orchestrator.

Run: python -m etl.pipeline

Extracts from the five independent operational databases, transforms into
a conformed vehicle/event model, and loads the star-schema warehouse
(data/vehicle_dwh.db). Safe to re-run any time — it is a full refresh.
"""
from etl.extract import extract_all
from etl.transform import transform
from etl.load import load


def run_pipeline() -> dict:
    print("=" * 70)
    print("ETL PIPELINE START")
    print("=" * 70)
    raw = extract_all()
    transformed = transform(raw)
    result = load(transformed)
    print("=" * 70)
    print("ETL PIPELINE COMPLETE")
    print("=" * 70)
    return result


if __name__ == "__main__":
    run_pipeline()
