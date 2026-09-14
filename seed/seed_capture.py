"""
Populate the Vehicle Capture / Road Camera database (vehicle_capture.db).

Run: python -m seed.seed_capture
"""
import config
import db
from seed.vehicle_master_data import VEHICLES


def seed():
    conn = db.get_connection(config.DB_CAPTURE)
    cur = conn.cursor()
    cur.execute("DELETE FROM vehicle_capture")

    count = 0
    for v in VEHICLES:
        for cap in v["captures"]:
            cur.execute(
                """
                INSERT INTO vehicle_capture
                    (plate_number, captured_timestamp, camera_id, location,
                     vehicle_type, detected_make, detected_model, detected_color,
                     confidence_score)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    v["plate"], cap["captured_timestamp"], cap["camera_id"], cap["location"],
                    cap["vehicle_type"], cap["detected_make"], cap["detected_model"],
                    cap["detected_color"], cap["confidence_score"],
                ),
            )
            count += 1

    conn.commit()
    conn.close()
    print(f"[seed_capture] inserted {count} rows into vehicle_capture.db")
    return count


if __name__ == "__main__":
    seed()
