from flask import Flask, jsonify, request
from flask_cors import CORS
from pathlib import Path
import joblib
import pandas as pd
import sqlite3


# ============================================================
# 1. APPLICATION CONFIGURATION
# ============================================================

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent.parent

ENERGY_MODEL_PATH = BASE_DIR / "models" / "energy_model.joblib"
ANOMALY_MODEL_PATH = BASE_DIR / "models" / "energy_anomaly_model.joblib"
DB_PATH = BASE_DIR / "database" / "smart_city.db"
DATASET_DIR = BASE_DIR / "dataset"


# ============================================================
# 2. LOAD MACHINE LEARNING MODELS
# ============================================================

energy_model = joblib.load(ENERGY_MODEL_PATH)
anomaly_model = joblib.load(ANOMALY_MODEL_PATH)


# ============================================================
# 3. DATABASE FUNCTIONS
# ============================================================

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

    try:
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

        return cursor.lastrowid

    finally:
        conn.close()


def get_energy_history():
    conn = get_connection()

    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT *
            FROM energy_readings
            ORDER BY timestamp DESC
        """)

        return [dict(row) for row in cursor.fetchall()]

    finally:
        conn.close()


# ============================================================
# 4. HOME / HEALTH CHECK API
# ============================================================

@app.route("/", methods=["GET"])
def home():

    return jsonify({
        "application": "Smart City Urban Analytics Platform",
        "message": "API is running successfully",
        "status": "success"
    })


# ============================================================
# 5. ENERGY CONSUMPTION PREDICTION
# ============================================================

@app.route("/api/energy/predict", methods=["POST"])
def predict_energy():

    try:
        data = request.get_json(silent=True)

        required_features = [
            "voltage",
            "current",
            "power_factor"
        ]

        # Check JSON object
        if not isinstance(data, dict):

            return jsonify({
                "status": "error",
                "error": "A JSON object is required"
            }), 400

        # Check required values
        if any(
            feature not in data or data[feature] is None
            for feature in required_features
        ):

            return jsonify({
                "status": "error",
                "error": "Please provide voltage, current, and power_factor"
            }), 400

        # Create model input
        input_data = pd.DataFrame([{
            feature: float(data[feature])
            for feature in required_features
        }])

        # Validate numbers
        if not all(
            input_data.iloc[0].map(
                lambda value: pd.notna(value)
                and abs(value) != float("inf")
            )
        ):

            return jsonify({
                "status": "error",
                "error": "Input values must be finite numbers"
            }), 400

        # ML prediction
        prediction = float(
            energy_model.predict(input_data)[0]
        )

        # Save result
        record_id = save_energy_result(
            voltage=float(data["voltage"]),
            current=float(data["current"]),
            power_factor=float(data["power_factor"]),
            predicted_energy=prediction
        )

        return jsonify({
            "status": "success",
            "record_id": record_id,
            "predicted_energy_usage": round(prediction, 2),
            "unit": "dataset units"
        })

    except (TypeError, ValueError, OverflowError):

        return jsonify({
            "status": "error",
            "error": "Input values must be numeric"
        }), 400

    except Exception:

        app.logger.exception(
            "Energy prediction failed"
        )

        return jsonify({
            "status": "error",
            "error": "Energy prediction failed"
        }), 500


# ============================================================
# 6. ENERGY ANOMALY DETECTION
# ============================================================

@app.route("/api/energy/anomaly", methods=["POST"])
def detect_anomaly():

    try:
        data = request.get_json(silent=True)

        required_features = [
            "energy_usage",
            "power_factor",
            "voltage",
            "current"
        ]

        # Check JSON object
        if not isinstance(data, dict):

            return jsonify({
                "status": "error",
                "error": "A JSON object is required"
            }), 400

        # Check required values
        if any(
            feature not in data or data[feature] is None
            for feature in required_features
        ):

            return jsonify({
                "status": "error",
                "error": (
                    "Please provide energy_usage, power_factor, "
                    "voltage, and current"
                )
            }), 400

        # Create model input
        input_data = pd.DataFrame([{
            feature: float(data[feature])
            for feature in required_features
        }])

        # Validate numbers
        if not all(
            input_data.iloc[0].map(
                lambda value: pd.notna(value)
                and abs(value) != float("inf")
            )
        ):

            return jsonify({
                "status": "error",
                "error": "Input values must be finite numbers"
            }), 400

        # ML anomaly detection
        result = anomaly_model.predict(input_data)[0]

        is_anomaly = result == -1

        # Save result
        record_id = save_energy_result(
            voltage=float(data["voltage"]),
            current=float(data["current"]),
            power_factor=float(data["power_factor"]),
            energy_usage=float(data["energy_usage"]),
            is_anomaly=int(is_anomaly)
        )

        return jsonify({
            "status": "success",
            "record_id": record_id,
            "anomaly": bool(is_anomaly),
            "classification": (
                "Potential anomaly"
                if is_anomaly
                else "Normal"
            )
        })

    except (TypeError, ValueError, OverflowError):

        return jsonify({
            "status": "error",
            "error": "Input values must be numeric"
        }), 400

    except Exception:

        app.logger.exception(
            "Anomaly detection failed"
        )

        return jsonify({
            "status": "error",
            "error": "Anomaly detection failed"
        }), 500


# ============================================================
# 7. ENERGY HISTORY API
# ============================================================

@app.route("/api/energy/history", methods=["GET"])
def energy_history():

    try:

        records = get_energy_history()

        return jsonify({
            "status": "success",
            "total_records": len(records),
            "records": records
        })

    except Exception:

        app.logger.exception(
            "Could not retrieve energy history"
        )

        return jsonify({
            "status": "error",
            "error": "Could not retrieve energy history"
        }), 500


# ============================================================
# 8. SENSOR DATA HELPER
# ============================================================

def get_sensor_data(filename, columns, measurements):

    file_path = DATASET_DIR / filename

    # Dataset doesn't exist
    if not file_path.exists():

        return None

    # Load CSV
    df = pd.read_csv(file_path)

    # --------------------------------------------------------
    # Summary statistics
    # --------------------------------------------------------

    summary = {
        "total_records": int(len(df)),

        "missing_values": int(
            df[measurements]
            .isna()
            .sum()
            .sum()
        ),

        "averages": {
            column: (
                round(float(df[column].mean()), 2)
                if df[column].notna().any()
                else None
            )
            for column in measurements
        }
    }

    # --------------------------------------------------------
    # Prepare records
    # --------------------------------------------------------

    records_df = df[columns].copy()

    # Convert missing values to JSON null
    records_df = records_df.astype(object).where(
        pd.notna(records_df),
        None
    )

    records = records_df.to_dict(
        orient="records"
    )

    return {
        "summary": summary,
        "records": records
    }


# ============================================================
# 9. AIR QUALITY API
# ============================================================

@app.route("/api/air-quality", methods=["GET"])
def air_quality():

    data = get_sensor_data(
        "air_quality_sensors.csv",

        [
            "timestamp",
            "device_id",
            "location",
            "pm25",
            "co2",
            "temperature",
            "humidity",
            "status"
        ],

        [
            "pm25",
            "co2",
            "temperature",
            "humidity"
        ]
    )

    if data is None:

        return jsonify({
            "status": "error",
            "error": "Air quality dataset not found"
        }), 404

    return jsonify({
        "status": "success",
        **data
    })


# ============================================================
# 10. TRAFFIC API
# ============================================================

@app.route("/api/traffic", methods=["GET"])
def traffic():

    data = get_sensor_data(
        "traffic_sensors.csv",

        [
            "timestamp",
            "device_id",
            "location",
            "traffic_count",
            "status"
        ],

        [
            "traffic_count"
        ]
    )

    if data is None:

        return jsonify({
            "status": "error",
            "error": "Traffic dataset not found"
        }), 404

    return jsonify({
        "status": "success",
        **data
    })


# ============================================================
# 11. WEATHER API
# ============================================================

@app.route("/api/weather", methods=["GET"])
def weather():

    data = get_sensor_data(
        "weather_station.csv",

        [
            "timestamp",
            "device_id",
            "location",
            "temperature",
            "humidity",
            "wind_speed",
            "precipitation",
            "status"
        ],

        [
            "temperature",
            "humidity",
            "wind_speed",
            "precipitation"
        ]
    )

    if data is None:

        return jsonify({
            "status": "error",
            "error": "Weather dataset not found"
        }), 404

    return jsonify({
        "status": "success",
        **data
    })


# ============================================================
# 12. RUN APPLICATION
# ============================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )