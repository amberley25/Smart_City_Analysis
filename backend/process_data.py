from pathlib import Path

from data_loader import load_all_data
from preprocessing import run_preprocessing_pipeline


BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_DIR = BASE_DIR / "dataset" / "processed"


def main():
    # Create the processed data folder
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # Load raw datasets
    datasets = load_all_data()

    # Run preprocessing
    processed_data = run_preprocessing_pipeline(datasets)

    # Save cleaned datasets
    for name, df in processed_data.items():
        output_path = PROCESSED_DIR / f"{name}_processed.csv"
        df.to_csv(output_path, index=False)
        print(f"Saved: {output_path.name}")

    print("\nAll datasets processed and saved successfully!")


if __name__ == "__main__":
    main()