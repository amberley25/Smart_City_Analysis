import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "smart_city.db"


def get_connection():
    return sqlite3.connect(DB_PATH)


def save_energy_result(
    voltage,
    current,
    power_factor,
    energy_usage=None,
    predicted_energy=None,
    is_anomaly=None
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO energy_readings (
            voltage,
            current,
            power_factor,
            energy_usage,
            predicted_energy,
            is_anomaly
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        voltage,
        current,
        power_factor,
        energy_usage,
        predicted_energy,
        is_anomaly
    ))

    conn.commit()
    record_id = cursor.lastrowid
    conn.close()

    return record_id


def get_energy_history():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT *
        FROM energy_readings
        ORDER BY timestamp DESC
    """)

    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return rows