"""SQLite persistence: sensor readings, detections and the prediction audit log."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .config import Settings

MEASURES = {
    "energy": ["energy_kwh", "voltage_v", "current_a", "power_factor"],
    "traffic": ["traffic_count", "avg_speed_kmh"],
    "air_quality": ["pm25_ugm3", "pm10_ugm3", "co2_ppm", "no2_ppb"],
    "weather": ["temperature_c", "humidity_pct", "wind_speed_ms", "precipitation_mm"],
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS energy (
    timestamp TEXT NOT NULL, zone TEXT NOT NULL, device_id TEXT NOT NULL,
    energy_kwh REAL, voltage_v REAL, current_a REAL, power_factor REAL, status TEXT NOT NULL,
    PRIMARY KEY (zone, timestamp)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS traffic (
    timestamp TEXT NOT NULL, zone TEXT NOT NULL, device_id TEXT NOT NULL,
    traffic_count REAL, avg_speed_kmh REAL, status TEXT NOT NULL,
    PRIMARY KEY (zone, timestamp)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS air_quality (
    timestamp TEXT NOT NULL, zone TEXT NOT NULL, device_id TEXT NOT NULL,
    pm25_ugm3 REAL, pm10_ugm3 REAL, co2_ppm REAL, no2_ppb REAL, status TEXT NOT NULL,
    PRIMARY KEY (zone, timestamp)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS weather (
    timestamp TEXT NOT NULL, zone TEXT NOT NULL, device_id TEXT NOT NULL,
    temperature_c REAL, humidity_pct REAL, wind_speed_ms REAL, precipitation_mm REAL, status TEXT NOT NULL,
    PRIMARY KEY (zone, timestamp)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_energy_ts ON energy (timestamp);
CREATE INDEX IF NOT EXISTS idx_traffic_ts ON traffic (timestamp);
CREATE INDEX IF NOT EXISTS idx_air_quality_ts ON air_quality (timestamp);
CREATE INDEX IF NOT EXISTS idx_weather_ts ON weather (timestamp);

CREATE TABLE IF NOT EXISTS energy_anomalies (
    timestamp TEXT NOT NULL, zone TEXT NOT NULL, score REAL NOT NULL,
    flagged INTEGER NOT NULL, reasons TEXT, true_type TEXT,
    PRIMARY KEY (zone, timestamp)
) WITHOUT ROWID;
CREATE INDEX IF NOT EXISTS idx_anomalies_flagged ON energy_anomalies (flagged, timestamp);

CREATE TABLE IF NOT EXISTS prediction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
    kind TEXT NOT NULL,
    zone TEXT NOT NULL,
    target_time TEXT,
    request TEXT NOT NULL,
    response TEXT NOT NULL
);
"""


def connect(settings: Settings) -> sqlite3.Connection:
    Path(settings.db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(settings.db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


@contextmanager
def session(settings: Settings):
    conn = connect(settings)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema(settings: Settings) -> None:
    with session(settings) as conn:
        conn.executescript(SCHEMA)


def ingest_csvs(settings: Settings) -> dict[str, int]:
    """Replace sensor tables with the contents of the dataset CSVs."""
    counts = {}
    with session(settings) as conn:
        conn.executescript(SCHEMA)
        for domain in MEASURES:
            frame = pd.read_csv(settings.csv_path(domain))
            frame["timestamp"] = pd.to_datetime(frame["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M:%S")
            conn.execute(f"DELETE FROM {domain}")
            frame.to_sql(domain, conn, if_exists="append", index=False)
            counts[domain] = len(frame)
    return counts


def read_frame(settings: Settings, domain: str) -> pd.DataFrame:
    """Full table as a DataFrame with parsed timestamps."""
    with session(settings) as conn:
        frame = pd.read_sql_query(f"SELECT * FROM {domain} ORDER BY timestamp, zone", conn)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    return frame


# Aggregation used when a series is requested at daily resolution.
DAILY_AGG = {
    "energy_kwh": "SUM",
    "voltage_v": "AVG",
    "current_a": "AVG",
    "power_factor": "AVG",
    "traffic_count": "SUM",
    "avg_speed_kmh": "AVG",
    "pm25_ugm3": "AVG",
    "pm10_ugm3": "AVG",
    "co2_ppm": "AVG",
    "no2_ppb": "AVG",
    "temperature_c": "AVG",
    "humidity_pct": "AVG",
    "wind_speed_ms": "AVG",
    "precipitation_mm": "SUM",
}

PRIMARY_MEASURE = {
    "energy": "energy_kwh",
    "traffic": "traffic_count",
    "air_quality": "pm25_ugm3",
    "weather": "temperature_c",
}
