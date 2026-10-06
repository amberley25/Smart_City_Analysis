from pathlib import Path
import pandas as pd

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset"

# Dataset filenames
DATASET_FILES = {
    "air_quality": "air_quality_sensors.csv",
    "energy": "energy_grid.csv",
    "traffic": "traffic_sensors.csv",
    "weather": "weather_station.csv"
}


def load_csv(file_path):
    """Load a CSV file and return a DataFrame."""
    if not file_path.exists():
        raise FileNotFoundError(
            f"Dataset not found: {file_path}"
        )

    return pd.read_csv(file_path)


def load_all_data():
    """Load all four Smart City datasets."""
    datasets = {}

    for name, filename in DATASET_FILES.items():
        file_path = DATASET_DIR / filename
        datasets[name] = load_csv(file_path)

        print(
            f"Loaded {name}: "
            f"{datasets[name].shape[0]} rows, "
            f"{datasets[name].shape[1]} columns"
        )

    return datasets


if __name__ == "__main__":
    data = load_all_data()

    print("\nAll datasets loaded successfully!")

    for name, df in data.items():
        print(f"\n{name.upper()}")
        print(df.head(3).to_string(index=False))