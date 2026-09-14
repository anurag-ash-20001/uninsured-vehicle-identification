"""
ETL - LOAD stage.

Loads the transformed vehicles/events bundle into the star-schema warehouse
(data/vehicle_dwh.db): DIM_VEHICLE, DIM_DATE, DIM_LOCATION, DIM_STATUS and
FACT_VEHICLE_EVENT. This is a full-refresh load (truncate + reload), which
is appropriate for a batch-oriented academic ETL over a small, regenerable
dataset — every run produces a byte-for-byte reproducible warehouse.
"""
from datetime import datetime

import config
import db


def _date_key(d) -> int:
    return int(d.strftime("%Y%m%d"))


def _get_or_create_date(cur, d, cache):
    if d is None:
        return None
    key = _date_key(d)
    if key in cache:
        return key
    cur.execute(
        "INSERT OR IGNORE INTO DIM_DATE (date_key, full_date, year, month, day, quarter, month_name) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (key, d.isoformat(), d.year, d.month, d.day, (d.month - 1) // 3 + 1, d.strftime("%B")),
    )
    cache[key] = True
    return key


def _get_or_create_location(cur, location_name, camera_id, cache):
    if not location_name and not camera_id:
        return None
    cache_key = (location_name, camera_id)
    if cache_key in cache:
        return cache[cache_key]
    cur.execute(
        "SELECT location_key FROM DIM_LOCATION WHERE location_name = ? AND camera_id IS ?",
        (location_name, camera_id),
    )
    row = cur.fetchone()
    if row:
        cache[cache_key] = row["location_key"]
        return row["location_key"]
    cur.execute(
        "INSERT INTO DIM_LOCATION (location_name, camera_id) VALUES (?, ?)",
        (location_name, camera_id),
    )
    cache[cache_key] = cur.lastrowid
    return cur.lastrowid


def _get_or_create_status(cur, category, value, cache):
    if not category or value is None:
        return None
    cache_key = (category, value)
    if cache_key in cache:
        return cache[cache_key]
    cur.execute(
        "SELECT status_key FROM DIM_STATUS WHERE status_category = ? AND status_value = ?",
        (category, value),
    )
    row = cur.fetchone()
    if row:
        cache[cache_key] = row["status_key"]
        return row["status_key"]
    cur.execute(
        "INSERT INTO DIM_STATUS (status_category, status_value) VALUES (?, ?)",
        (category, value),
    )
    cache[cache_key] = cur.lastrowid
    return cur.lastrowid


def load(transformed: dict) -> dict:
    conn = db.get_connection(config.DB_DWH)
    cur = conn.cursor()

    # Full refresh: clear fact then dims (fact has FK-like references to dims)
    cur.execute("DELETE FROM FACT_VEHICLE_EVENT")
    cur.execute("DELETE FROM DIM_VEHICLE")
    cur.execute("DELETE FROM DIM_DATE")
    cur.execute("DELETE FROM DIM_LOCATION")
    cur.execute("DELETE FROM DIM_STATUS")
    conn.commit()

    # ---------------- DIM_VEHICLE ----------------
    vehicle_key_by_id = {}
    now = datetime.now().isoformat(sep=" ", timespec="seconds")
    for vid, attrs in transformed["vehicles"].items():
        cur.execute(
            """
            INSERT INTO DIM_VEHICLE (vehicle_identifier, make, model, color, vehicle_type,
                                      fuel_type, owner_name, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (vid, attrs["make"], attrs["model"], attrs["color"], attrs["vehicle_type"],
             attrs["fuel_type"], attrs["owner_name"], now),
        )
        vehicle_key_by_id[vid] = cur.lastrowid
    conn.commit()

    # ---------------- FACT_VEHICLE_EVENT (+ dims on the fly) ----------------
    date_cache, location_cache, status_cache = {}, {}, {}
    fact_rows = 0
    for e in transformed["events"]:
        vehicle_key = vehicle_key_by_id.get(e["vehicle_identifier"])
        if vehicle_key is None:
            continue
        date_key = _get_or_create_date(cur, e["event_date"], date_cache)
        location_key = _get_or_create_location(cur, e["location_name"], e["camera_id"], location_cache)
        status_key = _get_or_create_status(cur, e["status_category"], e["status_value"], status_cache)

        cur.execute(
            """
            INSERT INTO FACT_VEHICLE_EVENT
                (vehicle_key, date_key, location_key, status_key, event_type,
                 event_value, source_system, load_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (vehicle_key, date_key, location_key, status_key, e["event_type"],
             e["event_value"], e["source_system"], now),
        )
        fact_rows += 1

    conn.commit()
    conn.close()

    print(f"[load] DIM_VEHICLE={len(vehicle_key_by_id)} FACT_VEHICLE_EVENT={fact_rows}")
    return {"dim_vehicle": len(vehicle_key_by_id), "fact_vehicle_event": fact_rows}
