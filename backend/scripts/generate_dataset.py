import pandas as pd
import numpy as np
import os
from datetime import datetime
import joblib

# Target variables
DEVICE_TYPES = [
    "Motherboard", "Hard Disk / SSD", "Monitor", "Mouse", 
    "Keyboard", "Smartphone", "Computer", "Printer", 
    "Projector", "Router / Switch"
]

# Base lifespan in years under IDEAL conditions
BASE_LIFESPAN = {
    "Motherboard": 8, "Hard Disk / SSD": 5, "Monitor": 7, 
    "Mouse": 3, "Keyboard": 4, "Smartphone": 4, 
    "Computer": 6, "Printer": 5, "Projector": 5, "Router / Switch": 6
}

def generate_maharashtra_dataset(num_samples=10000):
    """
    Generates a synthetic dataset of IT lab equipment in Maharashtra.
    Incorporates regional factors like dust, humidity, and power quality.
    """
    np.random.seed(42)
    
    data = []
    
    for _ in range(num_samples):
        device = np.random.choice(DEVICE_TYPES)
        base_life = BASE_LIFESPAN[device]
        
        # 1. Environmental Factors (Maharashtra Specific)
        # Rural/Semi-Urban (High Dust, High Temp) vs Coastal (High Humidity)
        region = np.random.choice(["Vidarbha/Marathwada", "Konkan/Mumbai", "Pune/Nashik"])
        
        if region == "Vidarbha/Marathwada":
            dust_index = np.random.uniform(0.6, 0.95) # High dust
            humidity_index = np.random.uniform(0.2, 0.5)
            temp_stress = np.random.uniform(0.7, 1.0) # High summer heat
        elif region == "Konkan/Mumbai":
            dust_index = np.random.uniform(0.3, 0.6)
            humidity_index = np.random.uniform(0.7, 1.0) # Coastal
            temp_stress = np.random.uniform(0.5, 0.8)
        else: # Pune/Nashik (Moderate)
            dust_index = np.random.uniform(0.4, 0.7)
            humidity_index = np.random.uniform(0.4, 0.7)
            temp_stress = np.random.uniform(0.4, 0.7)
            
        # 2. Operational Factors
        power_outage_freq = np.random.choice(["Low", "Medium", "High"], p=[0.2, 0.5, 0.3])
        if power_outage_freq == "High":
            power_surge_damage = np.random.uniform(0.6, 0.9)
        elif power_outage_freq == "Medium":
            power_surge_damage = np.random.uniform(0.3, 0.6)
        else:
            power_surge_damage = np.random.uniform(0.0, 0.3)
            
        usage_hours_per_day = np.random.uniform(2, 10) # IT Lab usage
        maintenance_frequency = np.random.choice(["Rare", "Annual", "Biannual"], p=[0.5, 0.3, 0.2])
        
        # 3. Calculate Actual Lifespan (The Target Variable)
        # Formula: Base Life * (Penalty Factors)
        
        # Dust kills cooling fans and causes short circuits (especially Motherboards, Projectors)
        dust_penalty = 1.0 - (dust_index * 0.2) if device in ["Motherboard", "Projector", "Computer"] else 1.0 - (dust_index * 0.05)
        
        # Humidity causes corrosion
        humidity_penalty = 1.0 - (humidity_index * 0.15) if device in ["Motherboard", "Hard Disk / SSD"] else 1.0 - (humidity_index * 0.05)
        
        # Power surges kill PSUs and drives
        power_penalty = 1.0 - (power_surge_damage * 0.3) if device in ["Computer", "Motherboard", "Hard Disk / SSD", "Router / Switch"] else 1.0 - (power_surge_damage * 0.1)
        
        # Usage wear and tear
        usage_penalty = 1.0 - ((usage_hours_per_day - 4) * 0.05) # Assume 4 hours is normal
        usage_penalty = max(0.5, usage_penalty) # Cap the penalty
        
        # Maintenance bonus
        maint_bonus = 1.2 if maintenance_frequency == "Biannual" else 1.1 if maintenance_frequency == "Annual" else 0.9
        
        # Final calculation with some random noise
        actual_lifespan = base_life * dust_penalty * humidity_penalty * power_penalty * usage_penalty * maint_bonus
        actual_lifespan = actual_lifespan * np.random.uniform(0.9, 1.1) # Add 10% random variance
        actual_lifespan = round(max(0.5, min(actual_lifespan, base_life * 1.2)), 2) # Cap limits
        
        # Determine Current Age (Randomly distributed between 0 and Actual Lifespan + 2)
        current_age = round(np.random.uniform(0, actual_lifespan + 1), 2)
        
        # Calculate Remaining Useful Life (RUL) -> This is what XGBoost will predict
        remaining_useful_life = max(0.0, round(actual_lifespan - current_age, 2))
        
        # Determine Failure Status
        is_failed = 1 if remaining_useful_life == 0 else 0
        
        data.append({
            "Device_Type": device,
            "Region": region,
            "Base_Lifespan": base_life,
            "Current_Age_Years": current_age,
            "Usage_Hours_Per_Day": round(usage_hours_per_day, 1),
            "Dust_Index": round(dust_index, 2),
            "Humidity_Index": round(humidity_index, 2),
            "Temperature_Stress": round(temp_stress, 2),
            "Power_Outage_Freq": power_outage_freq,
            "Maintenance_Frequency": maintenance_frequency,
            "Actual_Total_Lifespan": actual_lifespan,
            "Remaining_Useful_Life": remaining_useful_life,
            "Is_Failed": is_failed
        })
        
    df = pd.DataFrame(data)
    
    # Save the dataset
    os.makedirs("backend/data/processed/synthetic", exist_ok=True)
    df.to_csv("backend/data/processed/synthetic/maharashtra_edu_ewaste.csv", index=False)
    print(f"✅ Generated {num_samples} records and saved to backend/data/processed/synthetic/maharashtra_edu_ewaste.csv")
    
    return df

if __name__ == "__main__":
    generate_maharashtra_dataset()
