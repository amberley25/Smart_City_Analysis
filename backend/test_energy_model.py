import joblib
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = BASE_DIR / "models" / "energy_model.joblib"
DATA_PATH = BASE_DIR / "dataset" / "energy_grid.csv"

# Load the trained model
model = joblib.load(MODEL_PATH)

# Load a valid example record
df = pd.read_csv(DATA_PATH)

sample = df[
    (df["status"] == "OK") &
    (df["energy_usage"].notna())
].iloc[[0]]

features = ["voltage", "current", "power_factor"]

X = sample[features]

# Make a prediction
prediction = model.predict(X)[0]

print("\nENERGY MODEL TEST")
print("-------------------------")
print("Input features:")
print(X.to_string(index=False))

print(f"\nActual energy usage: {sample['energy_usage'].iloc[0]}")
print(f"Predicted energy usage: {prediction:.2f}")

print("\nModel loaded and prediction completed successfully!")