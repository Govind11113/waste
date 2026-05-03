import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
import os

def train_lifespan_models():
    print("🚀 Starting XGBoost & Random Forest Training...")
    
    # 1. Load Data
    data_path = "backend/data/processed/synthetic/maharashtra_edu_ewaste.csv"
    if not os.path.exists(data_path):
        print(f"❌ Error: Dataset not found at {data_path}")
        return
        
    df = pd.read_csv(data_path)
    print(f"✅ Loaded {len(df)} records.")
    
    # 2. Preprocessing
    # Features (X) and Target (y)
    # We want to predict Remaining_Useful_Life
    features = [
        "Device_Type", "Region", "Base_Lifespan", "Current_Age_Years", 
        "Usage_Hours_Per_Day", "Dust_Index", "Humidity_Index", 
        "Temperature_Stress", "Power_Outage_Freq", "Maintenance_Frequency"
    ]
    
    X = df[features].copy()
    y = df["Remaining_Useful_Life"]
    
    # Label Encoding for Categorical Variables
    label_encoders = {}
    categorical_cols = ["Device_Type", "Region", "Power_Outage_Freq", "Maintenance_Frequency"]
    
    for col in categorical_cols:
        le = LabelEncoder()
        X[col] = le.fit_transform(X[col])
        label_encoders[col] = le
        
    # Split the data
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # 3. Train Models
    
    # Model A: Random Forest (Baseline)
    print("\n🌲 Training Random Forest Regressor...")
    rf_model = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_preds = rf_model.predict(X_test)
    rf_mae = mean_absolute_error(y_test, rf_preds)
    rf_r2 = r2_score(y_test, rf_preds)
    print(f"Random Forest - MAE: {rf_mae:.2f} years | R2 Score: {rf_r2:.4f}")
    
    # Model B: XGBoost (High Performance)
    print("\n⚡ Training XGBoost Regressor...")
    xgb_model = XGBRegressor(
        n_estimators=200, 
        max_depth=6, 
        learning_rate=0.1, 
        subsample=0.8,
        random_state=42
    )
    xgb_model.fit(X_train, y_train)
    xgb_preds = xgb_model.predict(X_test)
    xgb_mae = mean_absolute_error(y_test, xgb_preds)
    xgb_r2 = r2_score(y_test, xgb_preds)
    print(f"XGBoost - MAE: {xgb_mae:.2f} years | R2 Score: {xgb_r2:.4f}")
    
    import pickle
    # 4. Save the best model and encoders
    os.makedirs("backend/models/lifespan", exist_ok=True)
    
    with open("backend/models/lifespan/xgboost_model.pkl", "wb") as f:
        pickle.dump(xgb_model, f)
        
    with open("backend/models/lifespan/rf_model.pkl", "wb") as f:
        pickle.dump(rf_model, f)
        
    with open("backend/models/lifespan/label_encoders.pkl", "wb") as f:
        pickle.dump(label_encoders, f)
    
    print("\n✅ Models and encoders saved to backend/models/lifespan/")
    print("Features expected by model:", features)

if __name__ == "__main__":
    train_lifespan_models()
