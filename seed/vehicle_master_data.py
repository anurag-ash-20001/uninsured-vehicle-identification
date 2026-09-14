"""
Single source of truth for the deterministic, fictional demo dataset.

Each of the five operational databases is populated independently by its own
seed_*.py script, but every script imports this module so that the SAME
underlying vehicle (identified across databases by different column names:
plate_number / registration_no / vehicle_registration_id / vehicle_no /
vehicle_identifier) gets consistent, correlated fictional attributes.

This does NOT violate the "independent databases" requirement: there is no
shared database, no foreign key, and no cross-database join anywhere in the
project. This module is only a fixture generator used once, at seed time,
so the fictional story is coherent for demonstration purposes.

Random generation uses a fixed seed (config.RANDOM_SEED) so re-running the
seed scripts always regenerates the identical dataset.
"""
import random
from datetime import date, datetime, timedelta

import config

random.seed(config.RANDOM_SEED)

TODAY = config.SIMULATION_TODAY

MAKES_MODELS = [
    ("Toyota", "Corolla"), ("Honda", "Civic"), ("Hyundai", "i20"),
    ("Maruti Suzuki", "Swift"), ("Tata", "Nexon"), ("Mahindra", "XUV500"),
    ("Ford", "EcoSport"), ("Kia", "Seltos"), ("Skoda", "Rapid"),
    ("Renault", "Kwid"), ("Volkswagen", "Polo"), ("Nissan", "Magnite"),
    ("MG", "Hector"), ("Honda", "City"), ("Toyota", "Innova"),
]
COLORS = ["White", "Black", "Silver", "Red", "Blue", "Grey", "Maroon", "Green"]
VEHICLE_TYPES = ["Sedan", "Hatchback", "SUV", "MUV"]
FUEL_TYPES = ["Petrol", "Diesel", "CNG", "Electric"]
INSURERS = [
    "National Shield Insurance", "TrustGuard General Insurance",
    "SecureDrive Insurance Co.", "UnityCover Insurance",
    "SafeRoad Assurance Ltd.",
]
LOCATIONS = [
    ("Camera-01", "NH-8 Toll Plaza, Gurugram"),
    ("Camera-02", "Ring Road Junction, Delhi"),
    ("Camera-03", "MG Road Signal, Bengaluru"),
    ("Camera-04", "Andheri Flyover, Mumbai"),
    ("Camera-05", "Anna Salai Checkpoint, Chennai"),
    ("Camera-06", "Sector-62 Crossing, Noida"),
    ("Camera-07", "Hitech City Road, Hyderabad"),
    ("Camera-08", "EM Bypass, Kolkata"),
]
FIRST_NAMES = ["Aarav", "Vivaan", "Ishaan", "Ananya", "Diya", "Kabir", "Meera",
               "Rohan", "Saanvi", "Aditya", "Priya", "Karan", "Neha", "Arjun",
               "Riya", "Yash", "Sanya", "Dev", "Tara", "Nikhil"]
LAST_NAMES = ["Sharma", "Verma", "Iyer", "Gupta", "Nair", "Kapoor", "Reddy",
              "Menon", "Chauhan", "Bhatia", "Joshi", "Malhotra", "Pillai",
              "Agarwal", "Rao"]

def _plate(n: int) -> str:
    return f"DL01AB{1000 + n}"

def _iso(d: date) -> str:
    return d.isoformat()

def _random_date_between(start: date, end: date) -> date:
    delta_days = (end - start).days
    if delta_days <= 0:
        return start
    return start + timedelta(days=random.randint(0, delta_days))


def _build_vehicle(n: int, category: str) -> dict:
    """Build one fully-specified fictional vehicle record set for index n (1..50)."""
    plate = _plate(n)
    make, model = MAKES_MODELS[n % len(MAKES_MODELS)]
    color = COLORS[n % len(COLORS)]
    vtype = VEHICLE_TYPES[n % len(VEHICLE_TYPES)]
    fuel = FUEL_TYPES[n % len(FUEL_TYPES)]
    owner_name = f"{FIRST_NAMES[n % len(FIRST_NAMES)]} {LAST_NAMES[n % len(LAST_NAMES)]}"
    owner_id = f"OWN{2000 + n}"

    v = {
        "plate": plate,
        "make": make,
        "model": model,
        "color": color,
        "vehicle_type": vtype,
        "fuel_type": fuel,
        "owner_id": owner_id,
        "owner_name": owner_name,
        "category": category,
        "captures": [],
        "insurance_policies": [],
        "theft_scrap": None,
        "registration": None,
    }

    # ---------------- Registration ----------------
    reg_date = TODAY - timedelta(days=random.randint(200, 2000))
    if category == "EXPIRED_REGISTRATION":
        reg_expiry = TODAY - timedelta(days=random.randint(5, 200))
        reg_status = "EXPIRED"
    else:
        reg_expiry = TODAY + timedelta(days=random.randint(60, 900))
        reg_status = "ACTIVE"
    if category == "NO_REGISTRATION":
        v["registration"] = None
    else:
        v["registration"] = {
            "registration_date": _iso(reg_date),
            "registration_expiry_date": _iso(reg_expiry),
            "registration_status": reg_status,
        }

    # ---------------- Insurance ----------------
    if category == "NO_INSURANCE":
        pass  # deliberately zero insurance rows
    elif category == "EXPIRED_INSURANCE":
        start = TODAY - timedelta(days=random.randint(400, 500))
        expiry = TODAY - timedelta(days=random.randint(10, 120))
        v["insurance_policies"].append({
            "insurer_name": INSURERS[n % len(INSURERS)],
            "policy_number": f"POL{100000 + n}",
            "policy_start_date": _iso(start),
            "policy_expiry_date": _iso(expiry),
            "insurance_status": "EXPIRED",
            "policy_type": "Comprehensive",
        })
    elif category == "MULTI_POLICY":
        # two expired historical policies + one currently active policy
        cursor = TODAY - timedelta(days=1000)
        for i in range(2):
            start = cursor
            expiry = start + timedelta(days=350)
            v["insurance_policies"].append({
                "insurer_name": INSURERS[(n + i) % len(INSURERS)],
                "policy_number": f"POL{100000 + n}{i}",
                "policy_start_date": _iso(start),
                "policy_expiry_date": _iso(expiry),
                "insurance_status": "EXPIRED",
                "policy_type": "Third-Party" if i == 0 else "Comprehensive",
            })
            cursor = expiry + timedelta(days=5)
        active_start = TODAY - timedelta(days=random.randint(30, 200))
        active_expiry = TODAY + timedelta(days=random.randint(60, 300))
        v["insurance_policies"].append({
            "insurer_name": INSURERS[n % len(INSURERS)],
            "policy_number": f"POL{100000 + n}9",
            "policy_start_date": _iso(active_start),
            "policy_expiry_date": _iso(active_expiry),
            "insurance_status": "ACTIVE",
            "policy_type": "Comprehensive",
        })
    else:
        # INSURED / STOLEN / RECOVERED / SCRAPPED / SHREDDED / SUSPICIOUS / default -> active policy
        start = TODAY - timedelta(days=random.randint(30, 300))
        expiry = TODAY + timedelta(days=random.randint(5, 300))
        v["insurance_policies"].append({
            "insurer_name": INSURERS[n % len(INSURERS)],
            "policy_number": f"POL{100000 + n}",
            "policy_start_date": _iso(start),
            "policy_expiry_date": _iso(expiry),
            "insurance_status": "ACTIVE",
            "policy_type": "Comprehensive",
        })

    # ------------ soon-to-expire variant (rotates in for demo query 7) ------------
    if category == "EXPIRING_SOON":
        start = TODAY - timedelta(days=200)
        expiry = TODAY + timedelta(days=random.randint(1, 29))
        v["insurance_policies"] = [{
            "insurer_name": INSURERS[n % len(INSURERS)],
            "policy_number": f"POL{100000 + n}",
            "policy_start_date": _iso(start),
            "policy_expiry_date": _iso(expiry),
            "insurance_status": "ACTIVE",
            "policy_type": "Comprehensive",
        }]

    # ---------------- Theft / Scrap ----------------
    if category == "STOLEN":
        v["theft_scrap"] = {
            "theft_status": "STOLEN",
            "theft_report_date": _iso(TODAY - timedelta(days=random.randint(2, 60))),
            "recovery_date": None,
            "scrapping_status": "NONE",
            "scrapping_date": None,
            "shredding_date": None,
            "authority_reference": f"FIR{5000 + n}",
            "remarks": "Reported stolen; case under investigation.",
        }
    elif category == "RECOVERED":
        report = TODAY - timedelta(days=random.randint(100, 300))
        recovered = report + timedelta(days=random.randint(5, 60))
        v["theft_scrap"] = {
            "theft_status": "RECOVERED",
            "theft_report_date": _iso(report),
            "recovery_date": _iso(recovered),
            "scrapping_status": "NONE",
            "scrapping_date": None,
            "shredding_date": None,
            "authority_reference": f"FIR{5000 + n}",
            "remarks": "Vehicle recovered and returned to owner.",
        }
    elif category == "SCRAPPED":
        v["theft_scrap"] = {
            "theft_status": "NONE",
            "theft_report_date": None,
            "recovery_date": None,
            "scrapping_status": "SCRAPPED",
            "scrapping_date": _iso(TODAY - timedelta(days=random.randint(10, 200))),
            "shredding_date": None,
            "authority_reference": f"SCRAP{6000 + n}",
            "remarks": "Vehicle certified scrapped at authorized facility.",
        }
    elif category == "SHREDDED":
        scrap_date = TODAY - timedelta(days=random.randint(150, 300))
        shred_date = scrap_date + timedelta(days=random.randint(10, 40))
        v["theft_scrap"] = {
            "theft_status": "NONE",
            "theft_report_date": None,
            "recovery_date": None,
            "scrapping_status": "SCRAPPED",
            "scrapping_date": _iso(scrap_date),
            "shredding_date": _iso(shred_date),
            "authority_reference": f"SCRAP{6000 + n}",
            "remarks": "End-of-life vehicle shredded.",
        }
    elif category == "SUSPICIOUS":
        # currently valid insurance but a past theft history -> suspicious pattern
        report = TODAY - timedelta(days=random.randint(300, 600))
        recovered = report + timedelta(days=random.randint(5, 40))
        v["theft_scrap"] = {
            "theft_status": "RECOVERED",
            "theft_report_date": _iso(report),
            "recovery_date": _iso(recovered),
            "scrapping_status": "NONE",
            "scrapping_date": None,
            "shredding_date": None,
            "authority_reference": f"FIR{5000 + n}",
            "remarks": "Past theft history recorded; monitor for repeat incidents.",
        }
    elif category in ("FILLER_CLEAN", "EXPIRED_REGISTRATION", "EXPIRING_SOON"):
        v["theft_scrap"] = {
            "theft_status": "NONE",
            "theft_report_date": None,
            "recovery_date": None,
            "scrapping_status": "NONE",
            "scrapping_date": None,
            "shredding_date": None,
            "authority_reference": None,
            "remarks": "No theft or scrapping history.",
        }
    # else: category has no theft_scrap row at all (simulates "missing info at source")

    # ---------------- Road captures ----------------
    n_captures = 1
    if category in ("STOLEN", "SCRAPPED", "SHREDDED"):
        n_captures = 2  # detected again AFTER the theft/scrap event -> critical risk demo
    for i in range(n_captures):
        ts = datetime.combine(TODAY, datetime.min.time()) - timedelta(
            days=random.randint(0, 5), hours=random.randint(0, 23)
        )
        # Randomized (not index-derived) so capture location is decorrelated
        # from the vehicle's category -- otherwise every vehicle of a given
        # category would always land in the same one or two cities.
        cam, loc = random.choice(LOCATIONS)
        v["captures"].append({
            "captured_timestamp": ts.isoformat(sep=" "),
            "camera_id": cam,
            "location": loc,
            "vehicle_type": vtype,
            "detected_make": make,
            "detected_model": model,
            "detected_color": color,
            "confidence_score": round(random.uniform(0.85, 0.99), 3),
        })

    return v


def build_dataset() -> list:
    """Return the deterministic list of config.NUM_VEHICLES fictional vehicle records."""
    # Vehicles 1-10 are the fixed, explicitly-specified demonstration vehicles.
    fixed_categories = {
        1: "INSURED",              # DL01AB1001 -> valid insurance
        2: "EXPIRED_INSURANCE",    # DL01AB1002 -> expired insurance
        3: "NO_INSURANCE",         # DL01AB1003 -> no insurance
        4: "STOLEN",               # DL01AB1004 -> stolen
        5: "SCRAPPED",             # DL01AB1005 -> scrapped
        6: "EXPIRED_REGISTRATION", # DL01AB1006 -> expired registration
        7: "SUSPICIOUS",           # DL01AB1007 -> valid insurance but suspicious/theft history
        8: "SHREDDED",             # DL01AB1008 -> shredded
        9: "RECOVERED",            # DL01AB1009 -> recovered stolen vehicle
        10: "MULTI_POLICY",        # DL01AB1010 -> multiple historical insurance policies
    }

    # Every remaining vehicle cycles deterministically through a weighted
    # rotation of categories, so the dataset satisfies every required
    # demonstration case many times over while still looking like a
    # realistic fleet (mostly clean/insured vehicles, with anomalies mixed in).
    rotation = (
        ["INSURED"] * 6
        + ["EXPIRED_INSURANCE"] * 2
        + ["NO_INSURANCE"] * 2
        + ["STOLEN"] * 1
        + ["RECOVERED"] * 1
        + ["SCRAPPED"] * 1
        + ["SHREDDED"] * 1
        + ["EXPIRED_REGISTRATION"] * 2
        + ["SUSPICIOUS"] * 1
        + ["MULTI_POLICY"] * 2
        + ["EXPIRING_SOON"] * 2
        + ["FILLER_CLEAN"] * 3
    )

    dataset = []
    for n in range(1, config.NUM_VEHICLES + 1):
        if n in fixed_categories:
            category = fixed_categories[n]
        else:
            category = rotation[n % len(rotation)]
        dataset.append(_build_vehicle(n, category))
    return dataset


VEHICLES = build_dataset()
