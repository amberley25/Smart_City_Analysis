import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from pathlib import Path
from data_loader import load_all_data
from preprocessing import (
    run_preprocessing_pipeline,
    preprocess_dataset
)


# Output directory
BASE_DIR = Path(__file__).resolve().parent.parent
EDA_DIR = BASE_DIR / "outputs" / "eda"
EDA_DIR.mkdir(parents=True, exist_ok=True)


# 1. Dataset analysis
def analyze_dataset(name, df):
    print(f"\n{'=' * 40}")
    print(f"EDA: {name.upper()}")
    print(f"{'=' * 40}")

    print("\nDataset shape:", df.shape)

    print("\nStatistical summary:")
    print(df.describe().round(2))

    print("\nMissing values:")
    print(df.isna().sum())

    print("\nSensor status:")
    if "status" in df.columns:
        print(df["status"].value_counts())


# 2. Distribution plots
def plot_distribution(df, column, title, filename):
    plt.figure(figsize=(8, 5))

    sns.histplot(df[column], kde=True)

    plt.title(title)
    plt.xlabel(column.replace("_", " ").title())
    plt.ylabel("Frequency")
    plt.tight_layout()

    plt.savefig(EDA_DIR / filename, dpi=300)
    plt.close()

    print(f"Saved plot: {filename}")


# 3. Sensor status comparison
def plot_sensor_status(datasets):
    status_counts = {}

    for name, df in datasets.items():
        status_counts[name] = df["status"].value_counts()

    status_df = pd.DataFrame(status_counts).fillna(0).T

    status_df.plot(kind="bar", figsize=(9, 5))

    plt.title("Sensor Status Across Datasets")
    plt.xlabel("Dataset")
    plt.ylabel("Number of Records")
    plt.xticks(rotation=0)
    plt.tight_layout()

    plt.savefig(EDA_DIR / "sensor_status.png", dpi=300)
    plt.close()

    print("Saved plot: sensor_status.png")


# 4. Correlation analysis
def analyze_correlations(datasets):
    for name, original_df in datasets.items():

        # Convert timestamps and numeric columns
        # without filling missing values
        df = preprocess_dataset(original_df)

        # Select numeric columns
        numeric_df = df.select_dtypes(include="number")

        # Exclude missing-value indicators
        numeric_df = numeric_df.drop(
            columns=[
                col for col in numeric_df.columns
                if col.endswith("_was_missing")
            ],
            errors="ignore"
        )

        if len(numeric_df.columns) < 2:
            print(f"Not enough numeric features in {name}")
            continue

        # Calculate correlations
        correlation = numeric_df.corr()

        # Save correlation values
        correlation.to_csv(
            EDA_DIR / f"{name}_correlation.csv"
        )

        # Generate heatmap
        plt.figure(figsize=(8, 6))

        sns.heatmap(
            correlation,
            annot=True,
            cmap="coolwarm",
            fmt=".2f",
            vmin=-1,
            vmax=1
        )

        plt.title(
            f"{name.replace('_', ' ').title()} Correlation"
        )
        plt.tight_layout()

        filename = f"{name}_correlation.png"
        plt.savefig(EDA_DIR / filename, dpi=300)
        plt.close()

        print(f"Saved correlation heatmap: {filename}")
        print(f"\n{name.upper()} CORRELATION:")
        print(correlation.round(2))


# 5. Main function
def main():
    # Load original datasets
    datasets = load_all_data()

    # Preprocess all datasets
    processed_data = run_preprocessing_pipeline(datasets)

    # Statistical analysis
    for name, df in processed_data.items():
        analyze_dataset(name, df)

    # Distribution plots
    plot_distribution(
        processed_data["air_quality"],
        "pm25",
        "Air Quality: PM2.5 Distribution",
        "air_quality_pm25.png"
    )

    plot_distribution(
        processed_data["energy"],
        "energy_usage",
        "Energy Usage Distribution",
        "energy_usage.png"
    )

    plot_distribution(
        processed_data["traffic"],
        "traffic_count",
        "Traffic Count Distribution",
        "traffic_count.png"
    )

    plot_distribution(
        processed_data["weather"],
        "temperature",
        "Weather: Temperature Distribution",
        "weather_temperature.png"
    )

    # Sensor status comparison
    plot_sensor_status(datasets)

    # Correlation analysis
    analyze_correlations(datasets)

    print("\nAll EDA analyses and visualizations completed!")


if __name__ == "__main__":
    main()