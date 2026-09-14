# Architecture

## Layers

1. **Source layer** — five independent SQLite databases (`data/*.db`), each with
   its own schema, primary keys, and vehicle-identifier column name. No foreign
   keys or views cross database boundaries.
2. **Mediator / federation layer** (`mediator/`) — accepts a raw plate string,
   normalizes it, decomposes a logical query into five source-specific SQL
   statements, executes each independently, and integrates the results into one
   `complete_vehicle_history` record, applying the rule engine along the way.
3. **Rule engine** (`ministry/rules.py`) — pure functions computing insurance
   status, suspicion status, risk level, and the ministry-reporting decision.
   Shared by the mediator (live lookups) and the warehouse refresh (batch).
4. **ETL layer** (`etl/`) — extracts full snapshots from the five sources,
   transforms them into a conformed vehicle/event model, and loads a star-schema
   warehouse (`data/vehicle_dwh.db`).
5. **Warehouse / materialized-view layer** (`dwh/`) — `refresh_views.py` rebuilds
   summary tables purely from the warehouse's own DIM/FACT tables;
   `queries.py` holds the 15 required analytics queries.
6. **Reporting layer** (`ministry/reporting.py`) — `report_to_ministry()` decides
   whether a report is warranted and persists it to `ministry.db`.
7. **Presentation layer** (`app.py`) — Streamlit GUI with 7 pages.

## Why a mediator instead of one shared database?

The problem statement models five separate real-world authorities (traffic police
camera network, insurance regulator, transport department, theft/scrap registry,
ministry). In reality these are operated by different organizations with different
schemas and no shared database — federation via a mediator is the realistic
integration pattern, and is what this project demonstrates end-to-end.
