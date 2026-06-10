"""
Train XGBoost + Random Forest lifespan models on the new corrected dataset.

Target: `remaining_life_yrs` (regression)
Features: raw inputs ONLY (no pre-computed factors — those would leak the target)
Compared: XGBoost, Random Forest, Linear Regression baseline, and the v2 formula.

Outputs:
  backend/models/lifespan/xgboost_model.pkl
  backend/models/lifespan/rf_model.pkl
  backend/models/lifespan/feature_columns.pkl
  backend/models/lifespan/training_metrics.json
"""

import os
import json
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor


# ─── Config ────────────────────────────────────────────────────────────────
DATASET_PATH = "/Users/govindraj/Desktop/ewaste_lifespan_dataset.csv"
MODEL_DIR = Path("/Users/govindraj/Desktop/E-waste/backend/models/lifespan")
MODEL_DIR.mkdir(parents=True, exist_ok=True)
RANDOM_STATE = 42

CATEGORICAL_FEATURES = [
    "device_type",
    "manufacturer",
    "region",
    "temperature",
    "environment",
    "power_quality",
    "maintenance",
]
NUMERIC_FEATURES = [
    "base_lifespan_yrs",
    "current_age_yrs",
    "daily_usage_hrs",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "remaining_life_yrs"


# ─── v2 Formula (ground truth for comparison) ──────────────────────────────
W = {"age": 0.30, "usage": 0.25, "temperature": 0.15, "power": 0.15, "environment": 0.10, "service": 0.05}
F_USAGE_BANDS = [(4, 1.00), (8, 0.85), (12, 0.70), (24, 0.50)]
F_TEMP = {"Cool": 0.90, "Normal": 0.75, "Hot": 0.50}
F_ENV = {"Clean": 0.90, "Normal": 0.70, "Harsh": 0.40}
F_POWER = {"UPS Protected": 0.90, "Direct Grid": 0.70, "Frequent Outages": 0.45}
F_MAINT = {"Regular": 0.90, "Occasional": 0.70, "No Service": 0.50, "None": 0.50}


def f_usage(h: float) -> float:
    for max_hr, score in F_USAGE_BANDS:
        if h <= max_hr:
            return score
    return 0.50


def predict_formula(row: pd.Series) -> float:
    base = row["base_lifespan_yrs"]
    age = row["current_age_yrs"]
    if age >= base:
        return 0.0
    f_age = max(0.0, 1.0 - age / base)
    f_u = f_usage(row["daily_usage_hrs"])
    f_t = F_TEMP[row["temperature"]]
    f_e = F_ENV[row["environment"]]
    f_p = F_POWER[row["power_quality"]]
    f_m = F_MAINT[row["maintenance"]]
    health = (
        W["age"] * f_age + W["usage"] * f_u + W["temperature"] * f_t +
        W["power"] * f_p + W["environment"] * f_e + W["service"] * f_m
    )
    health = max(0.0, min(1.0, health))
    raw = base * health - age
    return max(0.0, min(raw, base - age))


# ─── Load data ─────────────────────────────────────────────────────────────
print("=" * 70)
print("  E-WASTE LIFESPAN MODEL TRAINING (v2 — corrected dataset)")
print("=" * 70)

if not os.path.exists(DATASET_PATH):
    raise FileNotFoundError(f"Dataset not found at {DATASET_PATH}")
df = pd.read_csv(DATASET_PATH)
print(f"\n[1/5] Loaded {len(df)} rows from {DATASET_PATH}")
print(f"      Columns: {list(df.columns[:8])}...")
print(f"      Device types: {df['device_type'].nunique()} unique")
print(f"      Manufacturers: {df['manufacturer'].nunique()} unique")
print(f"      Failed devices: {df['failed'].sum()} ({df['failed'].mean()*100:.1f}%)")
print(f"      Mean target (remaining_life_yrs): {df[TARGET_COLUMN].mean():.2f}")


# ─── Build X, y ────────────────────────────────────────────────────────────
X = df[FEATURE_COLUMNS].copy()
y = df[TARGET_COLUMN].astype(float)

# Preprocessor: one-hot for categoricals, pass-through for numerics
preprocessor = ColumnTransformer(
    transformers=[
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
        ("num", "passthrough", NUMERIC_FEATURES),
    ],
    remainder="drop",
)


# ─── Train/test split ──────────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=RANDOM_STATE
)
print(f"\n[2/5] Split: {len(X_train)} train / {len(X_test)} test")

# Fit the preprocessor
X_train_t = preprocessor.fit_transform(X_train)
X_test_t = preprocessor.transform(X_test)
print(f"      Feature matrix shape after encoding: {X_train_t.shape}")


# ─── Train 3 models ────────────────────────────────────────────────────────
def evaluate(name, preds, truth):
    mae = mean_absolute_error(truth, preds)
    rmse = np.sqrt(mean_squared_error(truth, preds))
    r2 = r2_score(truth, preds)
    print(f"   {name:30s}  MAE={mae:.3f}y  RMSE={rmse:.3f}y  R²={r2:.4f}")
    return {"mae": round(float(mae), 3), "rmse": round(float(rmse), 3), "r2": round(float(r2), 4)}


print("\n[3/5] Training models...")
print("-" * 70)

# Model 1: Linear Regression (baseline)
lr = LinearRegression()
lr.fit(X_train_t, y_train)
lr_preds = lr.predict(X_test_t)
lr_preds_clipped = np.clip(lr_preds, 0, None)  # life can't be negative
lr_metrics = evaluate("Linear Regression", lr_preds_clipped, y_test)

# Model 2: Random Forest
rf = RandomForestRegressor(
    n_estimators=200,
    max_depth=12,
    min_samples_leaf=2,
    random_state=RANDOM_STATE,
    n_jobs=-1,
)
rf.fit(X_train_t, y_train)
rf_preds = rf.predict(X_test_t)
rf_preds_clipped = np.clip(rf_preds, 0, None)
rf_metrics = evaluate("Random Forest", rf_preds_clipped, y_test)

# Model 3: XGBoost
xgb = XGBRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.08,
    subsample=0.85,
    colsample_bytree=0.85,
    reg_alpha=0.1,
    reg_lambda=1.0,
    random_state=RANDOM_STATE,
    n_jobs=-1,
    verbosity=0,
)
xgb.fit(X_train_t, y_train)
xgb_preds = xgb.predict(X_test_t)
xgb_preds_clipped = np.clip(xgb_preds, 0, None)
xgb_metrics = evaluate("XGBoost", xgb_preds_clipped, y_test)

# Model 4: v2 Formula (no training — pure math)
formula_preds = X_test.apply(predict_formula, axis=1).values
formula_metrics = evaluate("v2 Formula (no training)", formula_preds, y_test)


# ─── Pick winner ───────────────────────────────────────────────────────────
print("\n[4/5] Selecting best model (by R²)...")
candidates = {
    "xgboost": (xgb_metrics["r2"], xgb_metrics, xgb, "xgb"),
    "random_forest": (rf_metrics["r2"], rf_metrics, rf, "rf"),
    "linear_regression": (lr_metrics["r2"], lr_metrics, lr, "lr"),
}
best_name = max(candidates, key=lambda k: candidates[k][0])
best_r2, best_metrics, best_model, best_kind = candidates[best_name]
print(f"   Best model: {best_name}  (R²={best_r2:.4f})")


# ─── Save artifacts ────────────────────────────────────────────────────────
print(f"\n[5/5] Saving artifacts to {MODEL_DIR}...")

# Full pipelines (preprocessor + model) so a single pickle holds everything
xgb_pipeline = Pipeline([("prep", preprocessor), ("model", xgb)])
rf_pipeline = Pipeline([("prep", preprocessor), ("model", rf)])

# Refit on full data so the saved models use 100% of the training data
xgb_pipeline.fit(X, y)
rf_pipeline.fit(X, y)

with open(MODEL_DIR / "xgboost_model.pkl", "wb") as f:
    pickle.dump(xgb_pipeline, f)
with open(MODEL_DIR / "rf_model.pkl", "wb") as f:
    pickle.dump(rf_pipeline, f)
with open(MODEL_DIR / "feature_columns.pkl", "wb") as f:
    pickle.dump(FEATURE_COLUMNS, f)
with open(MODEL_DIR / "categorical_features.pkl", "wb") as f:
    pickle.dump(CATEGORICAL_FEATURES, f)
with open(MODEL_DIR / "numeric_features.pkl", "wb") as f:
    pickle.dump(NUMERIC_FEATURES, f)

metrics_path = MODEL_DIR / "training_metrics.json"
metrics = {
    "dataset_path": DATASET_PATH,
    "n_rows": len(df),
    "n_features_after_encoding": int(X_train_t.shape[1]),
    "train_size": len(X_train),
    "test_size": len(X_test),
    "models": {
        "linear_regression": lr_metrics,
        "random_forest": rf_metrics,
        "xgboost": xgb_metrics,
        "v2_formula": formula_metrics,
    },
    "best_model": best_name,
    "feature_columns": FEATURE_COLUMNS,
    "target": TARGET_COLUMN,
}
with open(metrics_path, "w") as f:
    json.dump(metrics, f, indent=2)


# ─── Feature importance (XGBoost) ──────────────────────────────────────────
cat_features = preprocessor.named_transformers_["cat"].get_feature_names_out(CATEGORICAL_FEATURES)
all_features = list(cat_features) + NUMERIC_FEATURES
importances = xgb.feature_importances_
imp_df = pd.DataFrame({"feature": all_features, "importance": importances})
imp_df = imp_df.sort_values("importance", ascending=False).head(15)

print("\n" + "=" * 70)
print("  TOP-15 FEATURE IMPORTANCES (XGBoost)")
print("=" * 70)
for _, row in imp_df.iterrows():
    bar = "█" * int(row["importance"] * 100)
    print(f"   {row['feature']:42s}  {row['importance']:.4f}  {bar}")


# ─── Final summary ─────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("  TRAINING COMPLETE")
print("=" * 70)
print(f"   Best model:        {best_name}")
print(f"   Best R²:           {best_r2:.4f}")
print(f"   Best MAE:          {best_metrics['mae']:.3f} years")
print(f"   Best RMSE:         {best_metrics['rmse']:.3f} years")
print(f"\n   Saved to:")
print(f"     {MODEL_DIR / 'xgboost_model.pkl'}")
print(f"     {MODEL_DIR / 'rf_model.pkl'}")
print(f"     {MODEL_DIR / 'feature_columns.pkl'}")
print(f"     {MODEL_DIR / 'training_metrics.json'}")
print(f"\n   Comparison table:")
print(f"     {'Model':<28} {'MAE':>8} {'RMSE':>8} {'R²':>8}")
print(f"     {'-'*28} {'-'*8} {'-'*8} {'-'*8}")
for name, m in [("Linear Regression", lr_metrics),
                ("Random Forest", rf_metrics),
                ("XGBoost", xgb_metrics),
                ("v2 Formula (no training)", formula_metrics)]:
    print(f"     {name:<28} {m['mae']:>8.3f} {m['rmse']:>8.3f} {m['r2']:>8.4f}")
