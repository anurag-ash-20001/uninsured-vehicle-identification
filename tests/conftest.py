"""
Test session bootstrap.

`pytest` must work standalone (Section 16), so this session-scoped, autouse
fixture rebuilds every database from scratch — schemas, all five seeded
sources, the ETL load, and the materialized-view refresh — exactly once
before any test runs. This also means the test suite doubles as an
end-to-end pipeline smoke test.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import db
from seed import seed_capture, seed_insurance, seed_registration, seed_theft_scrap, seed_ministry
from etl.pipeline import run_pipeline
from dwh.refresh_views import refresh_all_views


@pytest.fixture(scope="session", autouse=True)
def bootstrap_full_dataset():
    db.init_all_schemas()
    seed_capture.seed()
    seed_insurance.seed()
    seed_registration.seed()
    seed_theft_scrap.seed()
    seed_ministry.seed()
    run_pipeline()
    refresh_all_views()
    yield
