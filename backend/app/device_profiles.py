"""
Single source of truth for device profiles across all backend routers.

Every device used in the classifier, lifespan predictor, and carbon calculator
must be defined here. Each router imports from this module instead of maintaining
its own copy.

Data sources & basis for the figures (see README "Data Sources & Citations"):
  * manufacturing_co2 (embodied carbon, kg CO2e): order-of-magnitude estimates
    derived from published manufacturer Life Cycle Assessments — primarily
    Apple Product Environmental Reports (https://www.apple.com/environment/),
    which report per-product manufacturing carbon using IPCC AR6 GWP-100, plus
    comparable OEM sustainability disclosures for appliances. Example anchors:
    smartphone ~70-80 kg, laptop ~150-300 kg, desktop ~300 kg.
  * base_lifespan / weight_kg / repair & replace costs: typical Indian
    educational-sector values (institutional procurement norms, OEM service
    pricing). These are planning estimates, not measured per-unit values, and
    are intended to be tuned with real institutional data.
  * recycling_co2: indicative CO2 saved by recovering materials through formal
    e-waste recycling vs virgin production.

NOTE: these are transparent, citable estimates for a decision-support tool — not
a certified product LCA. Replace with device-specific LCA data where available.
"""

DEVICE_PROFILES = {
    "Laptop": {
        "weight_kg": 2.0,
        "manufacturing_co2": 200,
        "annual_co2": 50,
        "recycling_co2": 18,
        "base_lifespan": 5,
        "base_repair_cost": 6000,
        "base_replace_cost": 50000,
        "default_tdp": 65,
    },
    "Computer": {
        "weight_kg": 10.0,
        "manufacturing_co2": 300,
        "annual_co2": 80,
        "recycling_co2": 25,
        "base_lifespan": 6,
        "base_repair_cost": 5000,
        "base_replace_cost": 35000,
        "default_tdp": 200,
    },
    "Smartphone": {
        "weight_kg": 0.2,
        "manufacturing_co2": 80,
        "annual_co2": 20,
        "recycling_co2": 10,
        "base_lifespan": 4,
        "base_repair_cost": 3000,
        "base_replace_cost": 15000,
        "default_tdp": 5,
    },
    "Monitor": {
        "weight_kg": 6.0,
        "manufacturing_co2": 180,
        "annual_co2": 40,
        "recycling_co2": 18,
        "base_lifespan": 7,
        "base_repair_cost": 1500,
        "base_replace_cost": 9000,
        "default_tdp": 35,
    },
    "Keyboard": {
        "weight_kg": 0.5,
        "manufacturing_co2": 20,
        "annual_co2": 2,
        "recycling_co2": 2,
        "base_lifespan": 4,
        "base_repair_cost": 200,
        "base_replace_cost": 1000,
        "default_tdp": 2,
    },
    "Mouse": {
        "weight_kg": 0.15,
        "manufacturing_co2": 15,
        "annual_co2": 1,
        "recycling_co2": 1,
        "base_lifespan": 3,
        "base_repair_cost": 100,
        "base_replace_cost": 500,
        "default_tdp": 2,
    },
    "Printer": {
        "weight_kg": 8.0,
        "manufacturing_co2": 120,
        "annual_co2": 30,
        "recycling_co2": 15,
        "base_lifespan": 5,
        "base_repair_cost": 2500,
        "base_replace_cost": 12000,
        "default_tdp": 50,
    },
    "Projector": {
        "weight_kg": 3.5,
        "manufacturing_co2": 150,
        "annual_co2": 40,
        "recycling_co2": 20,
        "base_lifespan": 5,
        "base_repair_cost": 6000,
        "base_replace_cost": 25000,
        "default_tdp": 250,
    },
    "Router / Switch": {
        "weight_kg": 1.0,
        "manufacturing_co2": 50,
        "annual_co2": 15,
        "recycling_co2": 5,
        "base_lifespan": 6,
        "base_repair_cost": 500,
        "base_replace_cost": 3000,
        "default_tdp": 15,
    },
    "Motherboard": {
        "weight_kg": 0.5,
        "manufacturing_co2": 80,
        "annual_co2": 10,
        "recycling_co2": 5,
        "base_lifespan": 8,
        "base_repair_cost": 2500,
        "base_replace_cost": 8000,
        "default_tdp": 50,
    },
    "Hard Disk / SSD": {
        "weight_kg": 0.2,
        "manufacturing_co2": 40,
        "annual_co2": 5,
        "recycling_co2": 2,
        "base_lifespan": 5,
        "base_repair_cost": 800,
        "base_replace_cost": 4000,
        "default_tdp": 8,
    },
    "Air Conditioner": {
        "weight_kg": 50.0,
        "manufacturing_co2": 600,
        "annual_co2": 250,
        "recycling_co2": 60,
        "base_lifespan": 10,
        "base_repair_cost": 5000,
        "base_replace_cost": 40000,
        "default_tdp": 1500,
    },
    "Television": {
        "weight_kg": 25.0,
        "manufacturing_co2": 220,
        "annual_co2": 60,
        "recycling_co2": 22,
        "base_lifespan": 8,
        "base_repair_cost": 8000,
        "base_replace_cost": 30000,
        "default_tdp": 100,
    },
    "Microwave": {
        "weight_kg": 12.0,
        "manufacturing_co2": 90,
        "annual_co2": 80,
        "recycling_co2": 8,
        "base_lifespan": 8,
        "base_repair_cost": 2500,
        "base_replace_cost": 12000,
        "default_tdp": 1100,
    },
    "Camera": {
        "weight_kg": 0.5,
        "manufacturing_co2": 60,
        "annual_co2": 5,
        "recycling_co2": 6,
        "base_lifespan": 5,
        "base_repair_cost": 3000,
        "base_replace_cost": 20000,
        "default_tdp": 5,
    },
    "Smartwatch": {
        "weight_kg": 0.05,
        "manufacturing_co2": 30,
        "annual_co2": 3,
        "recycling_co2": 3,
        "base_lifespan": 3,
        "base_repair_cost": 2000,
        "base_replace_cost": 10000,
        "default_tdp": 2,
    },
    "Battery": {
        "weight_kg": 2.0,
        "manufacturing_co2": 30,
        "annual_co2": 5,
        "recycling_co2": 4,
        "base_lifespan": 3,
        "base_repair_cost": 1500,
        "base_replace_cost": 4500,
        "default_tdp": 0,
    },
    "Washing Machine": {
        "weight_kg": 35.0,
        "manufacturing_co2": 400,
        "annual_co2": 60,
        "recycling_co2": 30,
        "base_lifespan": 10,
        "base_repair_cost": 4000,
        "base_replace_cost": 25000,
        "default_tdp": 500,
    },
    "Refrigerator": {
        "weight_kg": 60.0,
        "manufacturing_co2": 500,
        "annual_co2": 150,
        "recycling_co2": 40,
        "base_lifespan": 12,
        "base_repair_cost": 5000,
        "base_replace_cost": 30000,
        "default_tdp": 150,
    },
    "Remote Control": {
        "weight_kg": 0.1,
        "manufacturing_co2": 8,
        "annual_co2": 1,
        "recycling_co2": 1,
        "base_lifespan": 6,
        "base_repair_cost": 150,
        "base_replace_cost": 600,
        "default_tdp": 0,
    },
}


def co2_profiles() -> dict:
    """Derived dict for classifier.py: {device: {manufacturing, annual, recycling}}."""
    return {
        name: {
            "manufacturing": p["manufacturing_co2"],
            "annual": p["annual_co2"],
            "recycling": p["recycling_co2"],
        }
        for name, p in DEVICE_PROFILES.items()
    }


def embodied_carbon() -> dict:
    """Derived dict for carbon.py: {device: embodied_kg}."""
    return {name: p["manufacturing_co2"] for name, p in DEVICE_PROFILES.items()}


def default_lifespan() -> dict:
    """Derived dict for carbon.py: {device: lifespan_years}."""
    return {name: p["base_lifespan"] for name, p in DEVICE_PROFILES.items()}
