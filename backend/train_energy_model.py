import joblib
import pandas as pd

from pathlib import Path

from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "dataset" / "energy_grid.csv"
MODEL_PATH = BASE_DIR / "models" / "energy_model.joblib"

FEATURES = ["voltage", "current", "power_factor"]
TARGET = "energy_usage"


def main():
    # Load original data
    df = pd.read_csv(DATA_PATH)

    # Keep only valid records with an observed target
    df = df[
        (df["status"] == "OK") &
        (df[TARGET].notna())
    ].copy()

    X = df[FEATURES]
    y = df[TARGET]

    print(f"Usable records: {len(df)}")
    print(f"Features: {FEATURES}")

    if len(df) < 10:
        print("Not enough records for reliable cross-validation.")
        return

    # Define candidate models
    models = {
        "Baseline": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DummyRegressor(strategy="mean"))
        ]),

        "Linear Regression": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("model", LinearRegression())
        ]),

        "Random Forest": Pipeline([
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestRegressor(
                n_estimators=100,
                max_depth=3,
                min_samples_leaf=2,
                random_state=42
            ))
        ])
    }

    # Five-fold cross-validation
    cv = KFold(
        n_splits=5,
        shuffle=True,
        random_state=42
    )

    results = {}

    for name, model in models.items():
        scores = cross_validate(
            model,
            X,
            y,
            cv=cv,
            scoring={
                "mae": "neg_mean_absolute_error",
                "r2": "r2"
            }
        )

        mae = -scores["test_mae"].mean()
        r2 = scores["test_r2"].mean()

        results[name] = {
            "model": model,
            "mae": mae,
            "r2": r2
        }

        print(f"\n{name}")
        print(f"Mean CV MAE: {mae:.2f}")
        print(f"Mean CV R²: {r2:.3f}")

    # Select the model with the lowest cross-validation MAE
    best_name = min(
        results,
        key=lambda name: results[name]["mae"]
    )

    best_model = results[best_name]["model"]

    # Train the selected model on all eligible records
    best_model.fit(X, y)

    # Save the trained model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(best_model, MODEL_PATH)

    print(f"\nSelected model: {best_name}")
    print(f"Saved model to: {MODEL_PATH}")


if __name__ == "__main__":
    main()