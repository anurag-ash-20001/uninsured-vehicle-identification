# Data Warehouse Design

## Why the warehouse schema differs from the operational schemas

The five operational databases are normalized-per-source: each stores exactly one
kind of record (a capture, a policy, a registration, a theft/scrap entry, a
ministry report), keyed by its own natural/surrogate key, optimized for fast
single-vehicle point lookups during live federation.

The warehouse (`data/vehicle_dwh.db`) instead needs to answer **analytical**
questions across the whole vehicle population ("how many vehicles are currently
uninsured?", "which locations see the most suspicious vehicles?") quickly, without
re-querying five live databases every time. That calls for a different design:

- **A single conformed vehicle dimension** (`DIM_VEHICLE`), with one surrogate
  `vehicle_key` per real-world vehicle, instead of five differently-keyed tables.
- **A shared `DIM_DATE`** so every event (detection, registration, insurance
  policy/expiry, theft, recovery, scrapping, shredding, ministry report) can be
  rolled up by year/month/quarter consistently, regardless of which source it
  came from.
- **`DIM_LOCATION` and `DIM_STATUS`** as small, reusable lookup dimensions instead
  of repeating text values across millions of rows.
- **One `FACT_VEHICLE_EVENT` table**, grain = one row per lifecycle event, tagged
  with `source_system` — this is what lets a single warehouse query answer
  questions that would otherwise require touching all five operational databases.

This is the classic operational-vs-analytical schema split: OLTP-style independent
sources feeding a denormalized, surrogate-keyed OLAP star schema.

## Materialized views (SQLite has none natively)

SQLite doesn't support `CREATE MATERIALIZED VIEW`, so `dwh/refresh_views.py`
implements the same idea as ordinary tables (`mv_vehicle_complete_history`,
`mv_vehicle_current_status`, `mv_uninsured_vehicles`, `mv_expired_insurance`,
`mv_stolen_or_scrapped_vehicles`) that are fully rebuilt on demand
(`python -m dwh.refresh_views`). Rebuilding reads only from the warehouse's own
`DIM_VEHICLE`/`FACT_VEHICLE_EVENT` tables (never the live operational databases),
reconstructs each vehicle's policy/registration/theft history from its fact
events, and re-applies the same `ministry/rules.py` business rules the mediator
uses for live lookups — which is why warehouse (batch) and mediator (live) answers
are guaranteed to agree (see `tests/test_etl.py`).
