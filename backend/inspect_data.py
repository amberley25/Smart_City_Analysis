import csv
from pathlib import Path

DATASET_DIR = Path(__file__).parent.parent / "dataset"

files = [
    "air_quality_sensors.csv",
    "energy_grid.csv",
    "traffic_sensors.csv",
    "weather_station.csv"
]

for filename in files:
    file_path = DATASET_DIR / filename

    print(f"\n{'=' * 50}")
    print(f"DATASET: {filename}")
    print("=" * 50)

    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    print("Columns:", reader.fieldnames)
    print("Total rows:", len(rows))

    if rows:
        print("Missing values:")

        for column in reader.fieldnames:
            missing = sum(
                1 for row in rows
                if not row[column].strip()
                or row[column].strip().lower() in ("nan", "null", "none")
            )
            print(f"  {column}: {missing}")

    print("\nFirst 3 rows:")
    for row in rows[:3]:
        print(row)