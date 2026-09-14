# Federation & SQL Decomposition

## The pattern

1. `mediator/identifier_mapper.py::normalize_identifier()` cleans the raw plate
   string (case, whitespace, hyphens) into the canonical form used to query every
   source.
2. `mediator/query_decomposer.py::decompose_vehicle_query()` builds five
   parameterized `SELECT` statements, one per source, each using that source's own
   identifier column name (`plate_number`, `registration_no`,
   `vehicle_registration_id`, `vehicle_no`, `vehicle_identifier`).
3. `mediator/federated_query.py::execute_federated_query()` opens a connection to
   each of the five `data/*.db` files **independently** and runs its query. A
   source that is unreachable or errors returns an error marker instead of
   crashing the whole federation (`_run_local_query`).
4. `mediator/integration.py::get_complete_vehicle_history()` merges the five raw
   result sets in Python, resolving naming conflicts (e.g. preferring
   `vehicle_make` from registration but falling back to `detected_make` from the
   camera when registration is missing) and applying the business rules
   (`ministry/rules.py`) to derive insurance/suspicion/risk/ministry-report status.

## Why this is real federation, not "fake" federation

- There is **no single database that holds all the tables** — five separate
  `.db` files exist on disk, verifiable independently with any SQLite tool.
- **No SQL statement ever joins across the five files.** Each decomposed query is
  self-contained SQL against exactly one source's own table.
- The combination step happens entirely in Python, after each source has already
  returned its own local result set — this is the definition of mediator-based
  federation over autonomous, heterogeneous sources.
- The GUI's **Federated Query Demonstration** page prints the exact SQL sent to
  each of the five sources, plus their individual result sets, before showing the
  integrated answer — making the decomposition/federation visibly real, not just
  claimed.
