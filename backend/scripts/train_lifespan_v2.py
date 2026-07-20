#!/usr/bin/env python3
"""Benchmark lifespan estimators on the reproducible synthetic dataset.

Compared methods:
  * deterministic seven-factor weighted formula (no fitting)
  * Linear Regression baseline
  * Random Forest Regressor
  * XGBoost Regressor
  * LightGBM Regressor

The dataset and holdout are synthetic. Results show how methods recover the
synthetic generator's relationships; they are not evidence of accuracy on real
institutional devices and do not test research hypotheses.

No artifacts are written unless ``--write-artifacts`` is supplied. That explicit
guard prevents accidental replacement of the committed v2 pipelines.

Run from ``backend/``:
    python3 scripts/train_lifespan_v2.py
    python3 scripts/train_lifespan_v2.py --write-artifacts
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pickle
from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBRegressor

try:
    from lightgbm import LGBMRegressor
except Exception as exc:  # Keep --help/import diagnostics usable with a clear failure.
    LGBMRegressor = None
    LIGHTGBM_IMPORT_ERROR = exc
else:
    LIGHTGBM_IMPORT_ERROR = None

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = BACKEND_DIR / "data" / "processed" / "synthetic" / "lifespan_dataset.csv"
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "models" / "lifespan"
DEFAULT_RANDOM_STATE = 42

CATEGORICAL_FEATURES = [
    "device_type",
    "manufacturer",
    "region",
    "temperature",
    "environment",
    "power_quality",
    "maintenance",
    "software_load",
]
NUMERIC_FEATURES = [
    "base_lifespan_yrs",
    "current_age_yrs",
    "daily_usage_hrs",
]
FEATURE_COLUMNS = CATEGORICAL_FEATURES + NUMERIC_FEATURES
TARGET_COLUMN = "remaining_life_yrs"
REQUIRED_COLUMNS = set(FEATURE_COLUMNS + [TARGET_COLUMN, "failed"])

# Seven operational factors: age, usage, temperature, power, environment,
# maintenance/service, and software/workload.
WEIGHTS = {
    "age": 0.25,
    "usage": 0.20,
    "temperature": 0.15,
    "power": 0.13,
    "environment": 0.10,
    "service": 0.05,
    "software": 0.12,
}
USAGE_BANDS = ((4, 1.00), (8, 0.85), (12, 0.70), (24, 0.50))
TEMPERATURE_SCORES = {"Cool": 0.90, "Normal": 0.75, "Hot": 0.50}
ENVIRONMENT_SCORES = {"Clean": 0.90, "Normal": 0.70, "Harsh": 0.40}
POWER_SCORES = {"UPS Protected": 0.90, "Direct Grid": 0.70, "Frequent Outages": 0.45}
MAINTENANCE_SCORES = {"Regular": 0.90, "Occasional": 0.70, "No Service": 0.50, "None": 0.50}
SOFTWARE_SCORES = {"Light": 0.92, "Office": 0.78, "Heavy": 0.55}

ARTIFACT_FILENAMES = (
    "xgboost_model.pkl",
    "rf_model.pkl",
    "lightgbm_model.pkl",
    "feature_columns.pkl",
    "categorical_features.pkl",
    "numeric_features.pkl",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help=f"input CSV (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"artifact directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_RANDOM_STATE, help="split/model random seed")
    parser.add_argument("--test-size", type=float, default=0.20, help="synthetic holdout fraction")
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="native model worker count; 1 is the deterministic default",
    )
    parser.add_argument(
        "--write-artifacts",
        action="store_true",
        help="explicitly replace v2 model/metadata artifacts in --output-dir",
    )
    return parser


def usage_score(hours: float) -> float:
    for maximum, score in USAGE_BANDS:
        if hours <= maximum:
            return score
    return 0.50


def predict_formula(row: pd.Series) -> float:
    """Mirror the API's deterministic seven-factor formula baseline."""
    base = float(row["base_lifespan_yrs"])
    age = float(row["current_age_yrs"])
    if base <= 0 or age >= base:
        return 0.0
    age_score = max(0.0, 1.0 - age / base)
    health = (
        WEIGHTS["age"] * age_score
        + WEIGHTS["usage"] * usage_score(float(row["daily_usage_hrs"]))
        + WEIGHTS["temperature"] * TEMPERATURE_SCORES.get(row["temperature"], 0.75)
        + WEIGHTS["power"] * POWER_SCORES.get(row["power_quality"], 0.70)
        + WEIGHTS["environment"] * ENVIRONMENT_SCORES.get(row["environment"], 0.70)
        + WEIGHTS["service"] * MAINTENANCE_SCORES.get(row["maintenance"], 0.70)
        + WEIGHTS["software"] * SOFTWARE_SCORES.get(row.get("software_load", "Office"), 0.78)
    )
    health = float(np.clip(health, 0.0, 1.0))
    return max(0.0, min(base * health - age, base - age))


def evaluate(name: str, predictions, truth) -> dict[str, float]:
    mae = float(mean_absolute_error(truth, predictions))
    rmse = float(np.sqrt(mean_squared_error(truth, predictions)))
    r2 = float(r2_score(truth, predictions))
    print(f"  {name:30s} MAE={mae:.3f}y RMSE={rmse:.3f}y R2={r2:.4f}")
    return {"mae": round(mae, 3), "rmse": round(rmse, 3), "r2": round(r2, 4)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(BACKEND_DIR.resolve()))
    except ValueError:
        return str(path.resolve())


def validate_dataset(frame: pd.DataFrame) -> None:
    missing = sorted(REQUIRED_COLUMNS.difference(frame.columns))
    if missing:
        raise ValueError(f"Dataset is missing required columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError("Dataset contains no rows")
    if frame[FEATURE_COLUMNS + [TARGET_COLUMN]].isnull().any().any():
        raise ValueError("Dataset contains nulls in required model columns")


def build_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                CATEGORICAL_FEATURES,
            ),
            ("num", "passthrough", NUMERIC_FEATURES),
        ],
        remainder="drop",
    )


def write_pickle(path: Path, value) -> None:
    with path.open("wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 < args.test_size < 1.0:
        raise ValueError("--test-size must be between 0 and 1")
    if args.jobs < 1:
        raise ValueError("--jobs must be at least 1")
    if LGBMRegressor is None:
        raise RuntimeError(
            "LightGBM is required for the declared comparison. Install the pinned "
            f"requirements first. Import error: {LIGHTGBM_IMPORT_ERROR}"
        )

    dataset_path = args.dataset.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    if not dataset_path.is_file():
        raise FileNotFoundError(
            f"Dataset not found: {dataset_path}\n"
            "Generate the default synthetic CSV with: python3 scripts/generate_dataset.py"
        )

    # "None" is a valid maintenance category, so disable pandas' default NA
    # token conversion rather than silently turning that level into NaN.
    frame = pd.read_csv(dataset_path, keep_default_na=False)
    validate_dataset(frame)
    features = frame[FEATURE_COLUMNS].copy()
    target = frame[TARGET_COLUMN].astype(float)

    print("=" * 76)
    print("E-WASTE LIFESPAN ESTIMATOR BENCHMARK (SYNTHETIC DATA ONLY)")
    print("=" * 76)
    print(f"Dataset: {display_path(dataset_path)}")
    print(f"Rows: {len(frame)}")
    print(f"Device types represented: {frame['device_type'].nunique()}")
    print("Evidence boundary: no real institutional observations are evaluated.")

    train_x, test_x, train_y, test_y = train_test_split(
        features,
        target,
        test_size=args.test_size,
        random_state=args.seed,
    )
    preprocessor = build_preprocessor()
    train_encoded = preprocessor.fit_transform(train_x)
    test_encoded = preprocessor.transform(test_x)
    print(f"Synthetic split: {len(train_x)} train / {len(test_x)} test")
    print(f"Encoded feature columns: {train_encoded.shape[1]}")

    linear = LinearRegression()
    random_forest = RandomForestRegressor(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        random_state=args.seed,
        n_jobs=args.jobs,
    )
    xgboost = XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=args.seed,
        n_jobs=args.jobs,
        verbosity=0,
    )
    lightgbm = LGBMRegressor(
        n_estimators=400,
        max_depth=-1,
        num_leaves=31,
        learning_rate=0.05,
        subsample=0.85,
        subsample_freq=1,
        colsample_bytree=0.85,
        random_state=args.seed,
        n_jobs=args.jobs,
        deterministic=True,
        force_col_wise=True,
        verbosity=-1,
    )

    print("\nSynthetic holdout comparison:")
    model_metrics: dict[str, dict[str, float]] = {}
    for key, label, model in (
        ("linear_regression", "Linear Regression", linear),
        ("random_forest", "Random Forest", random_forest),
        ("xgboost", "XGBoost", xgboost),
        ("lightgbm", "LightGBM", lightgbm),
    ):
        model.fit(train_encoded, train_y)
        predictions = np.clip(model.predict(test_encoded), 0, None)
        model_metrics[key] = evaluate(label, predictions, test_y)

    formula_predictions = test_x.apply(predict_formula, axis=1).to_numpy()
    model_metrics["seven_factor_formula"] = evaluate(
        "Seven-factor formula (unfit)", formula_predictions, test_y
    )

    trained_keys = ("linear_regression", "random_forest", "xgboost", "lightgbm")
    best_model = max(trained_keys, key=lambda key: model_metrics[key]["r2"])

    category_names = preprocessor.named_transformers_["cat"].get_feature_names_out(
        CATEGORICAL_FEATURES
    )
    encoded_names = list(category_names) + NUMERIC_FEATURES
    top_importances_frame = (
        pd.DataFrame(
            {"feature": encoded_names, "importance": xgboost.feature_importances_}
        )
        .sort_values(("importance"), ascending=False)
        .head(15)
    )
    top_importances = [
        {"feature": str(row.feature), "importance": round(float(row.importance), 8)}
        for row in top_importances_frame.itertuples(index=False)
    ]

    metrics = {
        "dataset_kind": "synthetic",
        "evidence_boundary": (
            "Holdout rows come from the same synthetic generator; these metrics do "
            "not establish real-world predictive validity or test hypotheses."
        ),
        "dataset_path": display_path(dataset_path),
        "n_rows": int(len(frame)),
        "device_types_represented": int(frame["device_type"].nunique()),
        "n_features_after_encoding": int(train_encoded.shape[1]),
        "train_size": int(len(train_x)),
        "test_size": int(len(test_x)),
        "random_state": int(args.seed),
        "models": model_metrics,
        "best_model_on_synthetic_holdout": best_model,
        "feature_columns": FEATURE_COLUMNS,
        "target": TARGET_COLUMN,
        "xgboost_top_feature_importances": top_importances,
    }

    print(f"\nBest trained method on this synthetic holdout: {best_model}")
    print("Do not present that ordering or the scores as validation on real devices.")

    if not args.write_artifacts:
        print("\nNo artifacts written. Pass --write-artifacts to replace v2 outputs explicitly.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)

    def save_pipeline(model, filename: str) -> None:
        pipeline = Pipeline(
            [("prep", clone(build_preprocessor())), ("model", clone(model))]
        )
        pipeline.fit(features, target)
        write_pickle(output_dir / filename, pipeline)

    save_pipeline(xgboost, "xgboost_model.pkl")
    save_pipeline(random_forest, "rf_model.pkl")
    save_pipeline(lightgbm, "lightgbm_model.pkl")
    write_pickle(output_dir / "feature_columns.pkl", FEATURE_COLUMNS)
    write_pickle(output_dir / "categorical_features.pkl", CATEGORICAL_FEATURES)
    write_pickle(output_dir / "numeric_features.pkl", NUMERIC_FEATURES)

    with (output_dir / "training_metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metrics, handle, indent=2)
        handle.write("\n")

    manifest = {
        filename: sha256(output_dir / filename) for filename in ARTIFACT_FILENAMES
    }
    with (output_dir / "model_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")

    print(f"\nWrote v2 artifacts to: {display_path(output_dir)}")
    print("The manifest contains only artifacts produced by this v2 trainer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
