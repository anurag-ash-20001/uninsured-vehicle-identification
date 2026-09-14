<div align="center">

# 🚗 Identification of Uninsured Vehicles While They Are on Road

A working demo that looks up a vehicle by number plate and tells you — in plain
English — whether it's insured, stolen, scrapped, or fine, by combining data
from **5 independent databases**.

*All data is 100% fictional, generated for this demo. No real people, vehicles, or government systems are involved.*

</div>

---

## What it does

Give it a number plate. It checks five separate record books (insurance,
registration, theft/scrap history, road-camera sightings, and government
reports) and gives you one simple answer:

> ✅ **ALL CLEAR** — Nothing wrong found.
> ⚠️ **WARNING** — On the road without valid insurance.
> 🚨 **URGENT** — Reported stolen or scrapped, and still on the road.

## Why it's interesting

- **5 separate SQLite databases**, each with its own schema and its own name
  for "vehicle ID" (`plate_number`, `registration_no`, `vehicle_registration_id`,
  `vehicle_no`, `vehicle_identifier`) — nothing is joined directly across them.
- A **mediator** resolves those differences: it decomposes one question into
  5 real SQL queries, runs each independently, and merges the results.
- A **data warehouse** (star schema) + refreshable summary tables answer
  fleet-wide analytics fast, without hitting the live databases.
- A rule engine decides insurance status, risk level, and whether a vehicle
  should be reported — automatically, from the data.
- 2,000 fictional vehicles, deterministic and reproducible every time.

## Quick start

```bash
pip install -r requirements.txt
python setup.py          # creates + populates all databases, builds the warehouse
streamlit run app.py     # opens the web app
```

Then open the app and try plate **`DL01AB1004`** (stolen) or **`DL01AB1002`**
(expired insurance).

## The app

Two simple views:

- **🔍 Check a Vehicle** — type a plate, get a plain-language answer. Expand
  "Where did this information come from?" to see the actual SQL sent to each
  of the 5 databases and their raw results.
- **📋 Browse & Filter** — filter every detected vehicle by insurance status,
  theft status, report reason, city, and date range. Answers questions like
  *"how many uninsured vehicles were seen in each city in the last 6 months?"*

## Try these plates

| Plate | What you'll see |
|---|---|
| `DL01AB1001` | Valid insurance — all clear |
| `DL01AB1002` | Expired insurance |
| `DL01AB1003` | No insurance on record |
| `DL01AB1004` | Reported stolen |
| `DL01AB1005` | Scrapped, but still detected on the road |
| `DL01AB1006` | Expired registration |
| `DL01AB1010` | Multiple past insurance policies |

## Other useful commands

```bash
pytest                       # run the automated test suite (34 tests)
python -m scripts.demo       # scripted walkthrough in the terminal
python -m scripts.validate_project   # full project health check
python -m etl.pipeline       # rebuild the warehouse from the 5 source DBs
python -m dwh.refresh_views  # rebuild the summary tables
```

## Project layout

```
app.py            the web app
config.py         paths & settings
setup.py          one-shot: create + seed + build warehouse
data/             the 6 SQLite databases (5 sources + 1 warehouse)
schemas/          SQL that defines every table
seed/             generates the fictional dataset
mediator/         looks up a plate across all 5 databases and combines results
etl/              loads the data warehouse from the 5 sources
dwh/              warehouse analytics queries + summary-table refresh
ministry/         business rules + report generation
tests/            automated tests (pytest)
scripts/          demo + validation scripts
docs/             deeper technical write-ups (architecture, schema, etc.)
```

## Want the technical details?

The short version above is meant to be a quick read. For the full write-up —
schema diagrams, why the databases are independent, how SQL decomposition and
federation work, warehouse design, business rules — see [`docs/`](docs/):

- [`docs/architecture.md`](docs/architecture.md) — how the pieces fit together
- [`docs/database_design.md`](docs/database_design.md) — the 5 schemas + why they're independent
- [`docs/federation.md`](docs/federation.md) — SQL decomposition & federation, explained
- [`docs/dwh.md`](docs/dwh.md) — the data warehouse and materialized views
- [`docs/demo.md`](docs/demo.md) — a guided walkthrough for demos

## Limitations

This is an academic simulation — fictional data, no real government service
is contacted, and SQLite is used for simplicity instead of separately-hosted
production databases.
