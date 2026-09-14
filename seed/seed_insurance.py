"""
Populate the Vehicle Insurance database (insurance.db).

Run: python -m seed.seed_insurance
"""
import config
import db
from seed.vehicle_master_data import VEHICLES


def seed():
    conn = db.get_connection(config.DB_INSURANCE)
    cur = conn.cursor()
    cur.execute("DELETE FROM insurance_policy")

    count = 0
    for v in VEHICLES:
        for pol in v["insurance_policies"]:
            cur.execute(
                """
                INSERT INTO insurance_policy
                    (registration_no, insurer_name, policy_number, policy_start_date,
                     policy_expiry_date, insurance_status, policy_type)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    v["plate"], pol["insurer_name"], pol["policy_number"],
                    pol["policy_start_date"], pol["policy_expiry_date"],
                    pol["insurance_status"], pol["policy_type"],
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"[seed_insurance] inserted {count} rows into insurance.db")
    return count


if __name__ == "__main__":
    seed()
