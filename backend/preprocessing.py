import pandas as pd


def preprocess_timestamp(df):
    """Convert timestamps to datetime and sort the data."""
    df = df.copy()

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Remove rows with invalid timestamps
    df = df.dropna(subset=["timestamp"])

    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)

    return df
def clean_numeric(df):
    """Convert sensor measurement columns to numeric values."""
    df = df.copy()

    # Columns that contain descriptive information
    excluded_columns = [
        "timestamp",
        "device_id",
        "location",
        "status"
    ]

    for column in df.columns:
        if column not in excluded_columns:
            df[column] = pd.to_numeric(
                df[column],
                errors="coerce"
            )

    return df

def preprocess_dataset(df):
    """Apply all basic preprocessing steps to a dataset."""
    df = preprocess_timestamp(df)
    df = clean_numeric(df)

    return df

def preprocess_all(datasets):
    """Preprocess all sensor datasets."""
    processed_data = {}

    for name, df in datasets.items():
        processed_data[name] = preprocess_dataset(df)

        print(
            f"{name}: "
            f"{len(processed_data[name])} rows processed"
        )

    return processed_data

def handle_missing_values(df):
    """Fill missing numeric values while preserving missingness information."""
    df = df.copy()

    numeric_columns = df.select_dtypes(include="number").columns

    for column in numeric_columns:
        if df[column].isna().any():
            # Record which values were originally missing
            df[f"{column}_was_missing"] = df[column].isna().astype(int)

            # Fill missing values with the column median
            median_value = df[column].median()
            df[column] = df[column].fillna(median_value)

    return df

def run_preprocessing_pipeline(datasets):
    """Preprocess and clean all sensor datasets."""
    processed_data = {}

    for name, df in datasets.items():
        print(f"\nProcessing {name}...")

        # Step 1: Convert timestamps and clean numeric columns
        df = preprocess_dataset(df)

        # Step 2: Handle missing values
        df = handle_missing_values(df)

        processed_data[name] = df

        print(f"Rows: {len(df)}")
        print(f"Remaining missing values: {df.isna().sum().sum()}")

    return processed_data