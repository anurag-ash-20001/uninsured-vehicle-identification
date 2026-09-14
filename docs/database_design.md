# Database Design

## Independence principles

- Each of the five operational databases is a **separate SQLite file**
  (`schemas/*.sql` → `data/*.db`), not a table in a shared database.
- Each has its **own auto-incrementing primary key** (`capture_id`, `policy_id`,
  `registration_id`, `record_id`, `report_id`).
- **No foreign keys reference another database.**
- The vehicle identifier column is **deliberately named differently** in every
  source (see the table in README section 6), even though the underlying value is
  the same real-world plate number — this is what forces genuine identifier
  mapping/translation in the mediator rather than a trivial `JOIN`.

## Indexes

Every source table indexes its vehicle-identifier column plus the columns most
used in the 15 analytics queries (`policy_expiry_date`, `theft_status`,
`scrapping_status`, `registration_status`, `report_status`, `severity`). This
matters for federation performance: each per-source query in
`mediator/query_decomposer.py` is a single indexed `WHERE id_column = ?` lookup,
so federating across 5 sources is 5 fast point-lookups rather than 5 table scans.

## Data warehouse schema

See [`docs/dwh.md`](dwh.md) for why the warehouse schema intentionally differs
from the operational schemas (denormalized star schema with surrogate keys vs.
five independent normalized operational schemas).
