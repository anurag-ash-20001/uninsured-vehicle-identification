"""
Central configuration for the Uninsured Vehicle Identification project.

All database paths and shared constants live here so every module
(schemas, seeders, mediator, ETL, DWH, GUI, tests) points at the same files.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
SCHEMA_DIR = os.path.join(BASE_DIR, "schemas")

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Five independent operational (source) databases + one analytical warehouse
# ---------------------------------------------------------------------------
DB_CAPTURE = os.path.join(DATA_DIR, "vehicle_capture.db")
DB_INSURANCE = os.path.join(DATA_DIR, "insurance.db")
DB_REGISTRATION = os.path.join(DATA_DIR, "registration.db")
DB_THEFT_SCRAP = os.path.join(DATA_DIR, "theft_scrap.db")
DB_MINISTRY = os.path.join(DATA_DIR, "ministry.db")
DB_DWH = os.path.join(DATA_DIR, "vehicle_dwh.db")

SCHEMA_FILES = {
    DB_CAPTURE: os.path.join(SCHEMA_DIR, "vehicle_capture_schema.sql"),
    DB_INSURANCE: os.path.join(SCHEMA_DIR, "insurance_schema.sql"),
    DB_REGISTRATION: os.path.join(SCHEMA_DIR, "registration_schema.sql"),
    DB_THEFT_SCRAP: os.path.join(SCHEMA_DIR, "theft_scrap_schema.sql"),
    DB_MINISTRY: os.path.join(SCHEMA_DIR, "ministry_schema.sql"),
    DB_DWH: os.path.join(SCHEMA_DIR, "dwh_schema.sql"),
}

# Reference "today" used for computing insurance/registration validity.
# Fixed so the deterministic seed data always evaluates the same way.
from datetime import date
SIMULATION_TODAY = date(2026, 9, 14)

RANDOM_SEED = 42

# Total number of fictional vehicles to generate across all five source
# databases. Vehicles 1-10 are always the fixed demonstration vehicles
# (DL01AB1001-DL01AB1010); the rest cycle deterministically through every
# required category (insured, expired, uninsured, stolen, scrapped, etc.)
NUM_VEHICLES = 2000
