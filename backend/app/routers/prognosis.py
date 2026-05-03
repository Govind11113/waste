import os
import pickle
import pandas as pd
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/predict", tags=["Prognosis"])

# Load ML Models and Encoders safely
xgboost_model = None
rf_model = None
label_encoders = None

try:
    model_dir = os.path.join(os.path.dirname(__file__), "..", "..", "models", "lifespan")
    
    with open(os.path.join(model_dir, "xgboost_model.pkl"), "rb") as f:
        xgboost_model = pickle.load(f)
        
    with open(os.path.join(model_dir, "rf_model.pkl"), "rb") as f:
        rf_model = pickle.load(f)
        
    with open(os.path.join(model_dir, "label_encoders.pkl"), "rb") as f:
        label_encoders = pickle.load(f)
        
    print("✅ Loaded XGBoost & RF models for Prognosis")
except Exception as e:
    print(f"⚠️ Warning: Could not load ML lifespan models: {e}")


CO2_PROFILES = {
    "Motherboard": {"manufacturing": 80, "annual": 10, "recycling": 5, "base_lifespan": 8},
    "Hard Disk / SSD": {"manufacturing": 40, "annual": 5, "recycling": 2, "base_lifespan": 5},
    "Monitor": {"manufacturing": 180, "annual": 40, "recycling": 18, "base_lifespan": 7},
    "Mouse": {"manufacturing": 15, "annual": 1, "recycling": 1, "base_lifespan": 3},
    "Keyboard": {"manufacturing": 20, "annual": 2, "recycling": 2, "base_lifespan": 4},
    "Smartphone": {"manufacturing": 80, "annual": 20, "recycling": 10, "base_lifespan": 4},
    "Computer": {"manufacturing": 300, "annual": 80, "recycling": 25, "base_lifespan": 6},
    "Printer": {"manufacturing": 120, "annual": 30, "recycling": 15, "base_lifespan": 5},
    "Projector": {"manufacturing": 150, "annual": 40, "recycling": 20, "base_lifespan": 5},
    "Router / Switch": {"manufacturing": 50, "annual": 15, "recycling": 5, "base_lifespan": 6}
}

COST_PROFILES = {
    "Motherboard": {"replace": 8000, "repair": 2500},
    "Hard Disk / SSD": {"replace": 4000, "repair": 800},
    "Monitor": {"replace": 9000, "repair": 1500},
    "Mouse": {"replace": 500, "repair": 100},
    "Keyboard": {"replace": 1000, "repair": 200},
    "Smartphone": {"replace": 15000, "repair": 3000},
    "Computer": {"replace": 35000, "repair": 4000},
    "Printer": {"replace": 12000, "repair": 2500},
    "Projector": {"replace": 25000, "repair": 6000},
    "Router / Switch": {"replace": 3000, "repair": 500}
}


class PredictRequest(BaseModel):
    device_type: str
    brand: str = "Generic"
    device_model: str = "Generic"
    region: str = "Pune/Nashik"
    manufacturing_year: int
    usage_hours_per_day: float = 4.0
    dust_index: float = 0.5
    humidity_index: float = 0.5
    temperature_stress: float = 0.5
    power_outage_freq: str = "Medium"
    maintenance_frequency: str = "Annual"

class PredictResponse(BaseModel):
    remaining_years: float
    health_percentage: float
    co2_avoided: float
    manufacturing_co2: float
    annual_co2: float
    recycling_co2: float
    age: float
    base_lifespan: int
    model_used: str
    repair_cost: float
    replace_cost: float


@router.post("/", response_model=PredictResponse)
def predict_lifespan(request: PredictRequest):

    current_year = datetime.now().year
    current_age = float(max(0, current_year - request.manufacturing_year))

    profile = CO2_PROFILES.get(request.device_type, CO2_PROFILES["Computer"])
    base_lifespan = profile["base_lifespan"]

    # 1. ML Prediction Phase
    remaining_years = 0.0
    model_used = "Simulation (Fallback)"

    if xgboost_model and label_encoders:
        try:
            # Prepare the feature DataFrame
            input_data = pd.DataFrame([{
                "Device_Type": request.device_type,
                "Region": request.region,
                "Base_Lifespan": base_lifespan,
                "Current_Age_Years": current_age,
                "Usage_Hours_Per_Day": request.usage_hours_per_day,
                "Dust_Index": request.dust_index,
                "Humidity_Index": request.humidity_index,
                "Temperature_Stress": request.temperature_stress,
                "Power_Outage_Freq": request.power_outage_freq,
                "Maintenance_Frequency": request.maintenance_frequency
            }])
            
            # Apply Label Encoders
            for col in ["Device_Type", "Region", "Power_Outage_Freq", "Maintenance_Frequency"]:
                # Handle unknown categories gracefully by using the first class if not found
                if input_data[col][0] in label_encoders[col].classes_:
                    input_data[col] = label_encoders[col].transform(input_data[col])
                else:
                    input_data[col] = 0 
            
            # Select Model based on user preference
            active_model = xgboost_model
            model_used = "XGBoost (High Precision)"
            
            # Predict RUL
            predicted_rul = float(active_model.predict(input_data)[0])
            
            # Sanity checks on ML output
            remaining_years = max(0.0, round(predicted_rul, 1))
            
        except Exception as e:
            print(f"ML Inference Error: {e}")
            # Fallback to simple formula
            remaining_years = max(0, base_lifespan - current_age)

    else:
        # Fallback if models aren't loaded
        remaining_years = max(0, base_lifespan - current_age)

    # 2. Analytics Phase
    # Calculate health percentage based on original base life vs remaining
    health_percentage = min(100.0, max(0.0, (remaining_years / base_lifespan) * 100))

    # Calculate environmental impact averted if repaired vs scrapped
    co2_avoided = profile["manufacturing"] * (remaining_years / base_lifespan)

    repair_cost = COST_PROFILES.get(request.device_type, {"repair": 1000})["repair"]
    replace_cost = COST_PROFILES.get(request.device_type, {"replace": 5000})["replace"]

    return PredictResponse(
        remaining_years=round(remaining_years, 1),
        health_percentage=round(health_percentage, 1),
        co2_avoided=round(co2_avoided, 1),
        manufacturing_co2=profile["manufacturing"],
        annual_co2=profile["annual"],
        recycling_co2=profile["recycling"],
        age=current_age,
        base_lifespan=base_lifespan,
        model_used=model_used,
        repair_cost=float(repair_cost),
        replace_cost=float(replace_cost)
    )


@router.get("/device-types")
async def get_device_types():
    return {"device_types": list(CO2_PROFILES.keys())}

