"""
Synthetic E-Waste Lifespan Dataset Generator (Maharashtra Educational Sector)
=============================================================================

Generates a reproducible dataset for the device-lifespan prediction models.

The schema matches EXACTLY what the backend (``app/routers/prognosis.py``) and
the trainer (``scripts/train_lifespan_v2.py``) consume, so the committed models
are reproducible from the CSV this script writes.

Feature columns (these are the model inputs — fi(M, T, E, U, P, S) from the
research formula):
    device_type        T  — type of device
    manufacturer          — OEM (used as a categorical signal)
    region                — Maharashtra agro-climatic zone
    manufacturing_year M  — year of manufacture
    base_lifespan_yrs     — ideal-condition lifespan for the device type
    current_age_yrs       — age = current_year - manufacturing_year
    daily_usage_hrs    U  — hours/day in use
    temperature        E  — thermal stress (Cool / Normal / Hot)
    environment        E  — dust/humidity (Clean / Normal / Harsh)
    power_quality      P  — supply quality (UPS Protected / Direct Grid / Frequent Outages)
    maintenance        S* — service regularity (Regular / Occasional / None)
    software_load      S  — workload class (Light / Office / Heavy)

Targets:
    remaining_life_yrs    — REGRESSION target (remaining useful life, years)
    failed                — 1 if remaining_life_yrs == 0 else 0

Run:
    cd backend && python3 scripts/generate_dataset.py            # default 2000 rows
    cd backend && python3 scripts/generate_dataset.py --rows 5000 --seed 7

Output:
    backend/data/processed/synthetic/lifespan_dataset.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

# Resolve repo paths relative to THIS file so the script is portable
# (scripts/ -> backend/ -> repo root). No hard-coded user paths.
BACKEND_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BACKEND_DIR / "data" / "processed" / "synthetic"
OUT_PATH = OUT_DIR / "lifespan_dataset.csv"

# ── Device universe (kept in sync with app/device_profiles.py) ──────────────
# base_lifespan_yrs mirrors DEVICE_PROFILES[...]["base_lifespan"].
BASE_LIFESPAN = {
    "Laptop": 5, "Computer": 6, "Smartphone": 4, "Monitor": 7,
    "Keyboard": 4, "Mouse": 3, "Printer": 5, "Projector": 5,
    "Router / Switch": 6, "Motherboard": 8, "Hard Disk / SSD": 5,
    "Air Conditioner": 10, "Television": 8, "Microwave": 8,
    "Camera": 5, "Smartwatch": 3, "Battery": 3,
    "Washing Machine": 10, "Refrigerator": 12,
}

# Plausible OEMs per device family — purely a categorical signal for the model.
MANUFACTURERS = {
    "Laptop": ["Dell", "HP", "Lenovo", "Acer", "Asus", "Apple"],
    "Computer": ["Dell", "HP", "Lenovo", "Acer", "Assembled"],
    "Smartphone": ["Samsung", "Xiaomi", "Apple", "Realme", "Vivo", "OnePlus"],
    "Monitor": ["Dell", "LG", "Samsung", "BenQ", "Acer"],
    "Keyboard": ["Logitech", "Dell", "HP", "Zebronics"],
    "Mouse": ["Logitech", "Dell", "HP", "Zebronics"],
    "Printer": ["HP", "Canon", "Epson", "Brother"],
    "Projector": ["Epson", "BenQ", "ViewSonic", "Sony"],
    "Router / Switch": ["TP-Link", "D-Link", "Cisco", "Netgear"],
    "Motherboard": ["Asus", "Gigabyte", "MSI", "Intel"],
    "Hard Disk / SSD": ["Seagate", "WD", "Samsung", "Crucial"],
    "Air Conditioner": ["Voltas", "LG", "Daikin", "Blue Star", "Samsung"],
    "Television": ["Samsung", "LG", "Sony", "Mi", "TCL"],
    "Microwave": ["LG", "Samsung", "IFB", "Bajaj"],
    "Camera": ["Canon", "Nikon", "Sony", "Logitech"],
    "Smartwatch": ["Samsung", "Apple", "Noise", "boAt"],
    "Battery": ["Exide", "Amaron", "Luminous", "Generic"],
    "Washing Machine": ["LG", "Samsung", "Whirlpool", "IFB"],
    "Refrigerator": ["LG", "Samsung", "Whirlpool", "Godrej"],
}

REGIONS = ["Vidarbha/Marathwada", "Konkan/Mumbai", "Pune/Nashik"]

# Categorical level sets — identical strings to the backend scoring tables in
# app/routers/prognosis.py so the trained model sees the same vocabulary.
TEMPERATURE = ["Cool", "Normal", "Hot"]
ENVIRONMENT = ["Clean", "Normal", "Harsh"]
POWER_QUALITY = ["UPS Protected", "Direct Grid", "Frequent Outages"]
MAINTENANCE = ["Regular", "Occasional", "None"]
SOFTWARE_LOAD = ["Light", "Office", "Heavy"]

# ── Health multipliers (mirror the backend's weighted-average factor scores) ─
F_USAGE_BANDS = [(4, 1.00), (8, 0.85), (12, 0.70), (24, 0.50)]
F_TEMP = {"Cool": 0.90, "Normal": 0.75, "Hot": 0.50}
F_ENV = {"Clean": 0.90, "Normal": 0.70, "Harsh": 0.40}
F_POWER = {"UPS Protected": 0.90, "Direct Grid": 0.70, "Frequent Outages": 0.45}
F_MAINT = {"Regular": 0.90, "Occasional": 0.70, "None": 0.50}
# Software load is the PPT's S factor — heavier workloads shorten life.
F_SOFTWARE = {"Light": 0.92, "Office": 0.78, "Heavy": 0.55}

# Region priors make the data regionally realistic (Maharashtra zones).
REGION_PRIORS = {
    "Vidarbha/Marathwada": {  # hot + dusty interior
        "temperature": [0.10, 0.35, 0.55],
        "environment": [0.20, 0.40, 0.40],
        "power_quality": [0.20, 0.45, 0.35],
    },
    "Konkan/Mumbai": {  # humid coastal, better grid
        "temperature": [0.20, 0.55, 0.25],
        "environment": [0.30, 0.45, 0.25],
        "power_quality": [0.45, 0.45, 0.10],
    },
    "Pune/Nashik": {  # moderate
        "temperature": [0.30, 0.50, 0.20],
        "environment": [0.40, 0.45, 0.15],
        "power_quality": [0.40, 0.45, 0.15],
    },
}


def _f_usage(h: float) -> float:
    for max_hr, score in F_USAGE_BANDS:
        if h <= max_hr:
            return score
    return 0.50


def _choice(rng: np.random.Generator, options, p=None):
    return options[rng.choice(len(options), p=p)]


def generate(num_rows: int = 2000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    current_year = 2025  # fixed reference year so the dataset is deterministic
    devices = list(BASE_LIFESPAN.keys())

    rows = []
    for _ in range(num_rows):
        device = _choice(rng, devices)
        base = BASE_LIFESPAN[device]
        manufacturer = _choice(rng, MANUFACTURERS[device])
        region = _choice(rng, REGIONS)
        priors = REGION_PRIORS[region]

        temperature = _choice(rng, TEMPERATURE, p=priors["temperature"])
        environment = _choice(rng, ENVIRONMENT, p=priors["environment"])
        power_quality = _choice(rng, POWER_QUALITY, p=priors["power_quality"])
        maintenance = _choice(rng, MAINTENANCE, p=[0.30, 0.45, 0.25])
        software_load = _choice(rng, SOFTWARE_LOAD, p=[0.35, 0.45, 0.20])

        daily_usage = float(np.round(rng.uniform(1.0, 14.0), 1))

        # Age uniformly across (0 .. base + 2) so we see healthy + dead units.
        current_age = float(np.round(rng.uniform(0.0, base + 2.0), 2))
        manufacturing_year = int(current_year - round(current_age))

        # Health = weighted average of factor scores (same weights as backend).
        f_age = max(0.0, 1.0 - current_age / base)
        health = (
            0.25 * f_age
            + 0.20 * _f_usage(daily_usage)
            + 0.15 * F_TEMP[temperature]
            + 0.13 * F_POWER[power_quality]
            + 0.10 * F_ENV[environment]
            + 0.05 * F_MAINT[maintenance]
            + 0.12 * F_SOFTWARE[software_load]
        )
        health = float(np.clip(health, 0.0, 1.0))

        # Effective achievable lifespan, then remaining = effective - age.
        effective_lifespan = base * (0.55 + 0.55 * health)  # ranges ~0.55x..1.1x base
        effective_lifespan *= rng.uniform(0.92, 1.08)  # noise
        effective_lifespan = min(effective_lifespan, base * 1.15)

        remaining = effective_lifespan - current_age
        # Clamp to [0, base - age] so we never promise beyond the design life.
        remaining = max(0.0, min(remaining, max(0.0, base - current_age)))
        remaining = float(np.round(remaining, 2))

        rows.append({
            "device_type": device,
            "manufacturer": manufacturer,
            "region": region,
            "manufacturing_year": manufacturing_year,
            "base_lifespan_yrs": base,
            "current_age_yrs": current_age,
            "daily_usage_hrs": daily_usage,
            "temperature": temperature,
            "environment": environment,
            "power_quality": power_quality,
            "maintenance": maintenance,
            "software_load": software_load,
            "remaining_life_yrs": remaining,
            "failed": int(remaining == 0.0),
        })

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the lifespan dataset.")
    parser.add_argument("--rows", type=int, default=2000, help="number of rows")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = generate(args.rows, args.seed)
    df.to_csv(OUT_PATH, index=False)

    print(f"Generated {len(df)} rows -> {OUT_PATH}")
    print(f"  Device types : {df['device_type'].nunique()}")
    print(f"  Failed units : {df['failed'].sum()} ({df['failed'].mean() * 100:.1f}%)")
    print(f"  Mean RUL     : {df['remaining_life_yrs'].mean():.2f} yrs")
    print(f"  Columns      : {list(df.columns)}")


if __name__ == "__main__":
    main()
