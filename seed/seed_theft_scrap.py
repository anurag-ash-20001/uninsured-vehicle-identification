"""
Populate the Vehicle Theft and Scrapping database (theft_scrap.db).

Run: python -m seed.seed_theft_scrap
"""
import config
import db
from seed.vehicle_master_data import VEHICLES


def seed():
    conn = db.get_connection(config.DB_THEFT_SCRAP)
    cur = conn.cursor()
    cur.execute("DELETE FROM theft_scrap_record")

    count = 0
    for v in VEHICLES:
        ts = v["theft_scrap"]
        if ts is None:
            continue  # some vehicles have no theft/scrap row at all (nothing to report)
        cur.execute(
            """
            INSERT INTO theft_scrap_record
                (vehicle_no, theft_status, theft_report_date, recovery_date,
                 scrapping_status, scrapping_date, shredding_date,
                 authority_reference, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                v["plate"], ts["theft_status"], ts["theft_report_date"], ts["recovery_date"],
                ts["scrapping_status"], ts["scrapping_date"], ts["shredding_date"],
                ts["authority_reference"], ts["remarks"],
            ),
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"[seed_theft_scrap] inserted {count} rows into theft_scrap.db")
    return count


if __name__ == "__main__":
    seed()
