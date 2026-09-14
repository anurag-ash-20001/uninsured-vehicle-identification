"""
Populate the Vehicle Registration database (registration.db).

Run: python -m seed.seed_registration
"""
import config
import db
from seed.vehicle_master_data import VEHICLES


def seed():
    conn = db.get_connection(config.DB_REGISTRATION)
    cur = conn.cursor()
    cur.execute("DELETE FROM vehicle_registration")

    count = 0
    for v in VEHICLES:
        reg = v["registration"]
        if reg is None:
            continue  # deliberately missing registration record (error-handling demo)
        cur.execute(
            """
            INSERT INTO vehicle_registration
                (vehicle_registration_id, owner_id, owner_name, registration_date,
                 registration_expiry_date, vehicle_make, vehicle_model, vehicle_type,
                 fuel_type, color, registration_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                v["plate"], v["owner_id"], v["owner_name"], reg["registration_date"],
                reg["registration_expiry_date"], v["make"], v["model"], v["vehicle_type"],
                v["fuel_type"], v["color"], reg["registration_status"],
            ),
        )
        count += 1

    conn.commit()
    conn.close()
    print(f"[seed_registration] inserted {count} rows into registration.db")
    return count


if __name__ == "__main__":
    seed()
