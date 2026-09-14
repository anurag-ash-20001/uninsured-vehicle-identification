# Demonstration Guide

## Quick start

```powershell
pip install -r requirements.txt
python setup.py
pytest
streamlit run app.py
```

## Suggested walkthrough for a grader/demo audience

1. **Data Sources page** — show the five independent `.db` files, their schemas,
   and that each uses a different vehicle-identifier column name.
2. **Federated Query Demonstration page** — type `DL01AB1004` (stolen vehicle) and
   show the five decomposed SQL statements running against five independent
   databases, then the integrated JSON result with `risk_level = CRITICAL`.
3. **Vehicle Search page** — try each of the 10 fixed demo vehicles
   (`DL01AB1001`-`DL01AB1010`) and show the tabs (Overview / Registration /
   Insurance / Theft-Scrap / Risk & Ministry) filling in per the table in the
   README.
4. **Dashboard page** — KPI cards + charts summarizing the whole fleet.
5. **Uninsured / Suspicious / Ministry Reports pages** — the warehouse-backed
   list views.
6. **Terminal**: `python -m scripts.demo` for a scripted, no-GUI walkthrough of
   decomposition → federation → integration for all 10 demo vehicles.
7. **Terminal**: `python -m scripts.validate_project` for the full Section 23
   validation checklist (PASS/FAIL report).

## Regenerating everything from scratch

The dataset is fully deterministic (`config.RANDOM_SEED`), so `python setup.py`
always reproduces byte-identical operational data, and `pytest` (which bootstraps
the same pipeline via `tests/conftest.py`) always passes on a clean checkout.
