import joblib
import pandas as pd

from pathlib import Path
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "dataset" / "energy_grid.csv"
MODEL_PATH = BASE_DIR / "models" / "energy_anomaly_model.joblib"

FEATURES = [
    "energy_usage",
    "power_factor",
    "voltage",
    "current"
]


def main():
    df = pd.read_csv(DATA_PATH)

    # Use records marked as OK
    df = df[df["status"] == "OK"].copy()

    X = df[FEATURES]

    # Build the anomaly detection pipeline
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("detector", IsolationForest(
            n_estimators=100,
            contamination="auto",
            random_state=42
        ))
    ])

    # Train the model
    model.fit(X)

    # Detect anomalies in the available records
    predictions = model.predict(X)

    df["anomaly"] = predictions == -1

    print("\nANOMALY DETECTION RESULTS")
    print("-------------------------")
    print("Records analyzed:", len(df))
    print("Normal readings:", (~df["anomaly"]).sum())
    print("Anomalous readings:", df["anomaly"].sum())

    print("\nDetected anomalies:")
    print(
        df.loc[
            df["anomaly"],
            ["device_id", "location"] + FEATURES
        ].to_string(index=False)
    )

    # Save the model
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    print(f"\nModel saved to: {MODEL_PATH}")


if __name__ == "__main__":
    main()