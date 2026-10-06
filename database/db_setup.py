import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smart_city.db"


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS energy_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            voltage REAL,
            current REAL,
            power_factor REAL,
            energy_usage REAL,
            predicted_energy REAL,
            is_anomaly INTEGER
        )
    """)

    conn.commit()
    conn.close()

    print("Database created successfully!")
    print(f"Location: {DB_PATH}")


if __name__ == "__main__":
    create_database()