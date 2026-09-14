"""
Populate the Ministry of Transportation Reporting database (ministry.db).

Unlike the other four seed scripts (which insert fixed fictional rows),
this one seeds ministry.db by actually RUNNING the federation + business
rules engine (mediator.integration + ministry.rules) against every vehicle
in the other four already-seeded databases, and calling report_to_ministry()
for every vehicle that qualifies under Section 12's rules. This doubles as
a live demonstration that the mediator and rule engine work end-to-end.

Must run AFTER seed_capture, seed_insurance, seed_registration, seed_theft_scrap.

Run: python -m seed.seed_ministry
"""
import config
import db
from seed.vehicle_master_data import VEHICLES
from ministry.reporting import report_to_ministry


def seed():
    conn = db.get_connection(config.DB_MINISTRY)
    conn.execute("DELETE FROM ministry_report")
    conn.commit()
    conn.close()

    created = 0
    evaluated = 0
    for v in VEHICLES:
        outcome = report_to_ministry(v["plate"])
        evaluated += 1
        if outcome["created"]:
            created += len(outcome["reports"])

    print(f"[seed_ministry] evaluated {evaluated} vehicles, created {created} report rows in ministry.db")
    return created


if __name__ == "__main__":
    seed()
