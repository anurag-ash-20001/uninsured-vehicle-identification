"""
Streamlit GUI for "Identification of Uninsured Vehicles While They Are on Road".

Run: streamlit run app.py

Deliberately minimal: one search box, one plain-English answer, and a small
summary strip. All the technical machinery (5 independent databases, SQL
decomposition, federation, business rules) still runs underneath every
search — it's just explained in plain language instead of shown as raw
tables and JSON.
"""
import sqlite3
from datetime import timedelta

import pandas as pd
import streamlit as st

import config
import dwh.queries as q
from mediator.federated_query import execute_federated_query_with_trace
from mediator.integration import get_complete_vehicle_history
from mediator.identifier_mapper import normalize_identifier
from ministry.reporting import report_to_ministry

st.set_page_config(page_title="Vehicle Insurance Checker", layout="centered")

DEMO_PLATES = [f"DL01AB{1000 + n}" for n in range(1, 11)]

STATUS_STYLE = {
    "CRITICAL": ("🚨", "#d62728", "URGENT"),
    "HIGH": ("⚠️", "#ff7f0e", "WARNING"),
    "MEDIUM": ("ℹ️", "#c99a00", "NOTE"),
    "LOW": ("✅", "#2ca02c", "ALL CLEAR"),
}

SOURCE_LABELS = {
    "capture": "Road camera sightings",
    "insurance": "Insurance records",
    "registration": "Registration records",
    "theft_scrap": "Theft / scrapping records",
    "ministry": "Government reports",
}


def read_one(sql):
    conn = sqlite3.connect(config.DB_DWH)
    try:
        row = conn.execute(sql).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# plain-language explanations
# ---------------------------------------------------------------------------
def insurance_sentence(h):
    if h["insurance_status"] == "INSURED":
        return "✅", f"Has valid insurance (with {h['insurance_company'] or 'an insurer'}), valid until {h['insurance_expiry_date']}."
    if h["insurance_status"] == "EXPIRED":
        return "⚠️", f"Insurance EXPIRED on {h['insurance_expiry_date']}. It is currently driving without valid cover."
    return "🚫", "No insurance record was found for this vehicle at all."


def registration_sentence(h):
    if h["registration_status"] == "ACTIVE":
        return "✅", f"Registration is active, valid until {h['registration_expiry_date']}."
    if h["registration_status"] == "EXPIRED":
        return "⚠️", f"Registration EXPIRED on {h['registration_expiry_date']}."
    return "❔", "No registration record was found for this vehicle."


def theft_sentence(h):
    s = h["suspicion_status"]
    if s == "STOLEN":
        return "🚨", f"This vehicle was reported STOLEN on {h['theft_report_date']} and has not been recovered."
    if s in ("SCRAPPED", "SHREDDED"):
        date = h["scrapping_date"] or h["shredding_date"]
        return "🚨", f"This vehicle was officially scrapped/destroyed on {date} — it should not be on the road at all."
    if s == "RECOVERED_HISTORY":
        return "ℹ️", f"This vehicle was stolen in the past but was recovered on {h['recovery_date']}. No current issue, just worth knowing."
    return "✅", "No theft or scrapping history. Clean record."


def overall_verdict(h):
    icon, color, label = STATUS_STYLE.get(h["risk_level"], STATUS_STYLE["LOW"])
    if h["risk_level"] == "CRITICAL":
        message = "This vehicle needs immediate attention — it is stolen or scrapped, and it is still on the road."
    elif h["risk_level"] == "HIGH":
        message = "This vehicle has a real problem: it is on the road without valid insurance."
    elif h["risk_level"] == "MEDIUM":
        message = "This vehicle has some history worth being aware of, but nothing urgent right now."
    else:
        message = "Nothing wrong found. Insurance and registration look fine, and there is no theft/scrap history."
    return icon, color, label, message


# ---------------------------------------------------------------------------
# page 1 — check a single vehicle
# ---------------------------------------------------------------------------
def page_check_vehicle():
    st.title("🚗 Vehicle Insurance Checker")
    st.write(
        "Type a number plate. This checks it automatically against insurance, "
        "registration, theft, and scrapping records, and tells you in plain "
        "language whether it's safe, uninsured, stolen, or scrapped."
    )

    with st.expander("How does this work?"):
        st.write(
            "There isn't one single record for a vehicle — insurance, registration, "
            "theft reports, and road-camera sightings are each kept in their own "
            "separate record book. This tool looks the plate number up in all of "
            "them, one by one, and combines what it finds into one simple answer."
        )

    total = read_one("SELECT COUNT(*) FROM mv_vehicle_current_status")
    uninsured = read_one("SELECT COUNT(*) FROM mv_uninsured_vehicles")
    trouble = read_one("SELECT COUNT(*) FROM mv_stolen_or_scrapped_vehicles")

    c1, c2, c3 = st.columns(3)
    c1.metric("Vehicles on record", f"{total:,}")
    c2.metric("Currently uninsured", f"{uninsured:,}")
    c3.metric("Stolen or scrapped", f"{trouble:,}")

    st.markdown("---")

    plate = st.text_input("Number plate", value="DL01AB1004", placeholder="e.g. DL01AB1004")
    go = st.button("Check this vehicle", type="primary")

    if not (go or plate):
        return
    if not plate.strip():
        st.warning("Please type a number plate first.")
        return

    try:
        h = get_complete_vehicle_history(plate)
    except ValueError as exc:
        st.error(str(exc))
        return

    if not any(h["sources_found"].values()):
        st.error(f"'{h['vehicle_identifier']}' was not found in any record book. Please check the plate number.")
        return

    icon, color, label, message = overall_verdict(h)
    st.markdown(
        f"""
        <div style="border-left: 6px solid {color}; padding: 12px 16px; border-radius: 6px; background-color: rgba(128,128,128,0.08);">
            <div style="font-size:1.3em; font-weight:600;">{icon} {label}: {h['vehicle_identifier']}</div>
            <div style="margin-top:4px;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    vehicle_desc = " ".join(filter(None, [h["color"], h["make"], h["model"]])) or "Vehicle"
    st.write(f"**{vehicle_desc}**" + (f" — last seen at {h['location']} on {h['capture_time']}." if h["capture_time"] else " — not seen by any road camera yet."))

    for icon, text in [insurance_sentence(h), registration_sentence(h), theft_sentence(h)]:
        st.write(f"{icon}  {text}")

    if h["ministry_report_required"]:
        st.write("")
        already = h["ministry_report_status"] is not None
        if already:
            st.info(f"A government report has already been filed for this vehicle (status: {h['ministry_report_status']}).")
        else:
            st.warning("This vehicle should be reported to the authorities.")
            if st.button("📨 Send report now"):
                outcome = report_to_ministry(h["vehicle_identifier"])
                st.success(f"Report sent ({len(outcome['reports'])} item(s) filed).")

    with st.expander("Where did this information come from? (technical details)"):
        st.write(
            "There is no single master table. This plate number was looked up "
            "**separately, by its own SQL query, in each of the 5 independent "
            "databases below** — then the results were combined into the answer above."
        )
        trace = execute_federated_query_with_trace(h["vehicle_identifier"])
        for key, label in SOURCE_LABELS.items():
            rows = trace[key]["results"]
            found = h["sources_found"][key]
            st.markdown(f"**{'✅' if found else '—'} {label}**")
            st.code(trace[key]["sql"], language="sql")
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True)
            else:
                st.caption("No matching row in this database.")


# ---------------------------------------------------------------------------
# page 2 — browse & filter every detected vehicle
# ---------------------------------------------------------------------------
def page_browse_filter():
    st.title("📋 Browse & Filter Vehicles")
    st.write(
        "Filter every road-camera sighting on record by insurance status, "
        "theft status, why it was reported, the city, and when it was seen — "
        "e.g. *\"how many uninsured vehicles were detected in each city during "
        "the last six months?\"*"
    )

    insurance_options = ["Any"] + q.distinct_insurance_statuses()
    theft_options = ["Any"] + q.distinct_theft_statuses()
    reason_options = ["Any"] + q.distinct_report_reasons()
    location_options = q.distinct_locations()

    col1, col2, col3 = st.columns(3)
    insurance_choice = col1.selectbox("Insurance status", insurance_options)
    theft_choice = col2.selectbox("Theft status", theft_options)
    reason_choice = col3.selectbox("Report reason", reason_options)

    locations_choice = st.multiselect("City / location (leave empty = all cities)", location_options)

    default_start = config.SIMULATION_TODAY - timedelta(days=180)
    date_range = st.date_input(
        "Captured between",
        value=(default_start, config.SIMULATION_TODAY),
        help="Defaults to the last six months.",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_from, date_to = date_range
    else:
        date_from, date_to = default_start, config.SIMULATION_TODAY

    rows = []
    if not locations_choice:
        locations_choice = [None]
    for loc in locations_choice:
        rows.extend(q.browse_vehicle_detections(
            insurance_status=None if insurance_choice == "Any" else insurance_choice,
            theft_status=None if theft_choice == "Any" else theft_choice,
            report_reason=None if reason_choice == "Any" else reason_choice,
            location=loc,
            date_from=date_from.isoformat(),
            date_to=date_to.isoformat(),
        ))

    if not rows:
        st.info("No vehicles match these filters.")
        return

    df = pd.DataFrame(rows)
    distinct_vehicles = df["vehicle_identifier"].nunique()

    c1, c2 = st.columns(2)
    c1.metric("Vehicles matching", f"{distinct_vehicles:,}")
    c2.metric("Sightings matching", f"{len(df):,}")

    st.subheader("Matching vehicles by city")
    by_city = (
        df.groupby("location")["vehicle_identifier"]
        .nunique()
        .sort_values(ascending=False)
        .rename("vehicle_count")
    )
    st.bar_chart(by_city)

    st.subheader("All matching sightings")
    st.dataframe(
        df[[
            "vehicle_identifier", "make", "model", "color", "location", "captured_date",
            "insurance_status", "theft_status", "scrapping_status", "risk_level",
            "ministry_report_required", "ministry_report_status",
        ]],
        use_container_width=True,
    )


# ---------------------------------------------------------------------------
# navigation
# ---------------------------------------------------------------------------
def main():
    page = st.sidebar.radio("View", ["🔍 Check a Vehicle", "📋 Browse & Filter"])
    if page == "🔍 Check a Vehicle":
        page_check_vehicle()
    else:
        page_browse_filter()


if __name__ == "__main__":
    main()
