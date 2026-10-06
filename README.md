# Smart City Urban Analytics Platform

A full-stack smart-city analytics application that combines sensor datasets, data preprocessing, exploratory data analysis, machine learning, anomaly detection, database persistence, REST APIs, and an interactive React dashboard.

> **Project Type:** Academic Full-Stack + Machine Learning Project  
> **Frontend:** React + Vite  
> **Backend:** Flask REST API  
> **Database:** SQLite  
> **Machine Learning:** Scikit-learn  
> **Development Environment:** Python 3.12 + Node.js

---

## 1. Project Overview

The **Smart City Urban Analytics Platform** demonstrates how data from multiple urban sensor domains can be collected, processed, analyzed, stored, and presented through a unified interactive dashboard.

The application currently works with four sensor domains:

- Air Quality
- Energy
- Traffic
- Weather

The platform combines conventional data analytics with machine-learning capabilities.

The Energy module additionally provides:

- Energy consumption prediction
- Potential anomaly detection
- Historical result storage
- Interactive visualization
- REST API integration

The project is implemented as a complete application rather than a standalone machine-learning notebook.

The React frontend communicates with the Flask backend through REST APIs, while SQLite provides persistent storage for energy prediction and anomaly results.

---

# 2. Objectives

The main objectives of the project are:

1. Integrate multiple smart-city sensor datasets into one application.
2. Clean and preprocess sensor data before analysis.
3. Perform exploratory data analysis and generate useful visualizations.
4. Build a machine-learning model for energy usage prediction.
5. Detect potentially unusual energy readings using anomaly detection.
6. Store prediction and anomaly results in a database.
7. Provide REST APIs for frontend-backend communication.
8. Build an interactive dashboard for viewing urban analytics.
9. Demonstrate how the system can be extended toward real-time smart-city monitoring.

---

# 3. Key Features

## 3.1 Interactive Dashboard

The main dashboard provides a high-level overview of the available urban analytics.

It includes:

- Energy prediction statistics
- Average PM2.5
- Traffic overview
- Potential anomaly count
- Energy analytics chart
- Weather snapshot
- Sensor overview
- City Intelligence insights

---

## 3.2 Energy Analytics

The Energy module provides:

- Energy consumption prediction
- Potential anomaly detection
- Interactive energy charts
- Historical prediction records
- Database persistence
- Input validation

---

## 3.3 Air Quality

The Air Quality module provides:

- PM2.5 visualization
- CO2 visualization
- Air-quality sensor information

---

## 3.4 Traffic

The Traffic module provides:

- Traffic-count visualization
- Traffic sensor information

---

## 3.5 Weather

The Weather module provides:

- Temperature trends
- Humidity trends
- Weather sensor information

---

# 4. System Architecture

```text
                    ┌──────────────────────────────┐
                    │       React Frontend         │
                    │          + Vite              │
                    │                              │
                    │  Dashboard                   │
                    │  Energy Analytics            │
                    │  Air Quality                  │
                    │  Traffic                      │
                    │  Weather                      │
                    └──────────────┬───────────────┘
                                   │
                              REST API / HTTP
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │       Flask Backend          │
                    │                              │
                    │  API Routes                  │
                    │  Data Access                 │
                    │  ML Inference                │
                    │  Validation                  │
                    │  Database Operations          │
                    └───────┬──────────────┬───────┘
                            │              │
                 ┌──────────┘              └───────────┐
                 ▼                                     ▼
       ┌──────────────────┐                 ┌──────────────────┐
       │    ML Models     │                 │ Sensor Datasets  │
       │                  │                 │                  │
       │ Linear Regression│                 │ Air Quality      │
       │ Isolation Forest │                 │ Energy           │
       │                  │                 │ Traffic          │
       └────────┬─────────┘                 │ Weather          │
                │                           └──────────────────┘
                ▼
       ┌──────────────────┐
       │    SQLite DB     │
       │                  │
       │ Energy Readings  │
       │ Predictions      │
       │ Anomaly Results  │
       └──────────────────┘
```

---

# 5. Application Workflow

```text
Sensor CSV Data
      │
      ▼
Data Loading
      │
      ▼
Data Preprocessing
      │
      ├──────────────► Exploratory Data Analysis
      │
      ▼
Machine Learning
      │
      ├──────────────► Energy Prediction
      │
      └──────────────► Anomaly Detection
                              │
                              ▼
                        Flask REST API
                              │
                              ▼
                       React Dashboard
                              │
                              ▼
                         SQLite Storage
```

---

# 6. Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Frontend Build Tool | Vite |
| Charts | Recharts |
| Icons | Lucide React |
| Backend | Flask |
| API | REST |
| Database | SQLite |
| Data Processing | Pandas, NumPy |
| Machine Learning | Scikit-learn |
| Model Persistence | Joblib |
| EDA / Visualization | Matplotlib, Seaborn |
| Development Environment | Python 3.12 + Node.js |

---

# 7. Dataset

The project uses four sensor datasets.

## 7.1 Air Quality Dataset

**File:**

```text
dataset/air_quality_sensors.csv
```

**Fields:**

- Timestamp
- Device ID
- Location
- PM2.5
- CO2
- Temperature
- Humidity
- Status

---

## 7.2 Energy Dataset

**File:**

```text
dataset/energy_grid.csv
```

**Fields:**

- Timestamp
- Device ID
- Location
- Energy Usage
- Power Factor
- Voltage
- Current
- Status

---

## 7.3 Traffic Dataset

**File:**

```text
dataset/traffic_sensors.csv
```

**Fields:**

- Timestamp
- Device ID
- Location
- Traffic Count
- Status

---

## 7.4 Weather Dataset

**File:**

```text
dataset/weather_station.csv
```

**Fields:**

- Timestamp
- Device ID
- Location
- Temperature
- Humidity
- Wind Speed
- Precipitation
- Status

---

# 8. Dataset Size

The current datasets contain:

| Dataset | Records |
|---|---:|
| Air Quality | 45 |
| Energy | 35 |
| Traffic | 50 |
| Weather | 40 |
| **Total** | **170** |

The datasets contain missing sensor values, which are handled during preprocessing.

Because the available datasets are relatively small and cover a limited time period, machine-learning results should be considered **experimental/prototype results** rather than production-scale performance measurements.

---

# 9. Data Preprocessing

The preprocessing pipeline is implemented in:

```text
backend/preprocessing.py
```

The pipeline performs several operations.

## 9.1 Timestamp Processing

Timestamp fields are converted into appropriate datetime representations for analysis.

---

## 9.2 Numeric Cleaning

Numeric sensor fields are converted into usable numerical representations.

---

## 9.3 Missing Value Handling

Missing numerical values are handled using **median-based imputation**.

Additional missing-value indicator columns are generated to retain information about whether an original value was missing.

---

## 9.4 Processed Data

Processed datasets are stored in:

```text
dataset/processed/
```

Files include:

```text
air_quality_processed.csv
energy_processed.csv
traffic_processed.csv
weather_processed.csv
```

---

# 10. Exploratory Data Analysis

Exploratory Data Analysis is performed using:

- Pandas
- Matplotlib
- Seaborn

The EDA workflow generates visualizations for:

- PM2.5
- Energy Usage
- Traffic Count
- Temperature
- Sensor Status
- Correlation analysis

Generated outputs are stored under:

```text
outputs/eda/
```

Typical outputs include:

```text
air_quality_pm25.png
energy_usage.png
traffic_count.png
weather_temperature.png
sensor_status.png
```

Correlation outputs are also generated for applicable datasets.

---

# 11. Machine Learning

## 11.1 Energy Prediction

Energy prediction is implemented as a supervised regression problem.

### Input Features

The model uses:

- Voltage
- Current
- Power Factor

### Target

```text
Energy Usage
```

### Models Compared

Three approaches were evaluated:

1. Dummy Regressor
2. Linear Regression
3. Random Forest Regressor

### Evaluation

Five-fold shuffled cross-validation was used during model comparison.

The evaluated results were:

| Model | MAE | R² |
|---|---:|---:|
| Dummy Regressor | 10.31 | -0.606 |
| Linear Regression | 3.90 | 0.780 |
| Random Forest | 4.21 | 0.702 |

Based on these results, **Linear Regression** was selected for the current prototype.

### Selected Model

```text
models/energy_model.joblib
```

### Reported Cross-Validation Results

```text
MAE: 3.90
R² : 0.780
```

The model was trained using **30 usable energy records** after filtering and preprocessing.

These results are based on a small dataset and should not be interpreted as evidence of production-level predictive accuracy.

---

# 12. Energy Anomaly Detection

The project also includes an exploratory anomaly-detection model using:

```text
Isolation Forest
```

The model uses energy-related variables including:

- Energy Usage
- Power Factor
- Voltage
- Current

The trained model is stored at:

```text
models/energy_anomaly_model.joblib
```

The current exploratory run identified:

```text
11 observations → Normal
19 observations → Potential Anomalies
```

These are **model-generated flags**, not confirmed real-world equipment failures.

---

# 13. Machine Learning Workflow

```text
Raw Energy Dataset
        │
        ▼
Data Cleaning
        │
        ▼
Missing Value Handling
        │
        ▼
Feature Selection
        │
        ├─────────────────────┐
        ▼                     ▼
   Regression          Anomaly Detection
        │                     │
        ▼                     ▼
Energy Prediction      Isolation Forest
        │                     │
        └──────────┬──────────┘
                   ▼
              Flask API
                   │
                   ▼
           React Dashboard
```

---

# 14. Database

The application uses **SQLite** for lightweight persistent storage.

Database file:

```text
database/smart_city.db
```

The `energy_readings` table stores fields including:

- ID
- Timestamp
- Voltage
- Current
- Power Factor
- Energy Usage
- Predicted Energy
- Anomaly Status

The database is used to persist prediction and anomaly-detection results.

Records remain available after:

- Browser refresh
- Backend restart

---

# 15. REST API

The Flask backend provides the following endpoints.

## 15.1 Health Check

```http
GET /
```

Returns application/API status.

---

## 15.2 Energy Prediction

```http
POST /api/energy/predict
```

### Request

```json
{
  "voltage": 230,
  "current": 2.2,
  "power_factor": 0.95
}
```

### Process

The endpoint:

1. Validates the input.
2. Converts the values into model features.
3. Runs the trained regression model.
4. Stores the result in SQLite.
5. Returns the prediction.

For the tested input:

```text
Voltage: 230
Current: 2.2
Power Factor: 0.95
```

the current trained model produced a prediction of approximately:

```text
510.36
```

This value is a model output for the available prototype dataset.

---

## 15.3 Energy Anomaly Detection

```http
POST /api/energy/anomaly
```

### Request

```json
{
  "energy_usage": 500,
  "power_factor": 0.95,
  "voltage": 230,
  "current": 2.2
}
```

The endpoint runs the Isolation Forest model and stores the resulting anomaly status.

---

## 15.4 Energy History

```http
GET /api/energy/history
```

Returns previously stored energy prediction/anomaly records.

---

## 15.5 Air Quality

```http
GET /api/air-quality
```

Returns air-quality sensor data used by the dashboard.

---

## 15.6 Traffic

```http
GET /api/traffic
```

Returns traffic sensor data used by the dashboard.

---

## 15.7 Weather

```http
GET /api/weather
```

Returns weather sensor data used by the dashboard.

---

# 16. Project Structure

```text
Smart_City_Analysis/
│
├── backend/
│   ├── app.py
│   ├── database.py
│   ├── db_setup.py
│   ├── data_loader.py
│   ├── preprocessing.py
│   ├── process_data.py
│   ├── eda.py
│   ├── train_energy_model.py
│   ├── test_energy_model.py
│   └── train_anomaly_model.py
│
├── database/
│   └── smart_city.db
│
├── dataset/
│   ├── air_quality_sensors.csv
│   ├── energy_grid.csv
│   ├── traffic_sensors.csv
│   ├── weather_station.csv
│   └── processed/
│       ├── air_quality_processed.csv
│       ├── energy_processed.csv
│       ├── traffic_processed.csv
│       └── weather_processed.csv
│
├── models/
│   ├── energy_model.joblib
│   └── energy_anomaly_model.joblib
│
├── notebooks/
│
├── outputs/
│   └── eda/
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   ├── index.css
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── README.md
│
├── requirements.txt
├── .gitignore
└── README.md
```

> Development-only directories such as `venv/`, `venv_py314_backup/`, and `frontend/node_modules/` should not be included in the submission archive.

---

# 17. Installation and Setup

## 17.1 Prerequisites

Install:

- Python 3.12
- Node.js
- npm
- Git (optional)

The project was developed and tested using Python 3.12.

---

# 18. Backend Setup

Open PowerShell in the project root:

```powershell
cd C:\Dev_Amb\Smart_City_Analysis
```

Activate the Python environment:

```powershell
.\venv\Scripts\Activate.ps1
```

Verify Python:

```powershell
python --version
```

Expected:

```text
Python 3.12.x
```

---

## 18.1 Install Python Dependencies

If `pip` is available:

```powershell
pip install -r requirements.txt
```

If the environment is managed using `uv`:

```powershell
uv pip install --python .\venv\Scripts\python.exe -r requirements.txt
```

---

# 19. Frontend Setup

Open another terminal:

```powershell
cd C:\Dev_Amb\Smart_City_Analysis\frontend
```

Install frontend dependencies:

```powershell
npm install
```

The frontend dependencies are defined in:

```text
frontend/package.json
```

---

# 20. Running the Application

The backend and frontend should be run in separate terminals.

## 20.1 Start Backend

From the project root:

```powershell
cd C:\Dev_Amb\Smart_City_Analysis
.\venv\Scripts\Activate.ps1
python backend/app.py
```

The Flask backend runs at:

```text
http://127.0.0.1:5000
```

---

## 20.2 Start Frontend

Open a second terminal:

```powershell
cd C:\Dev_Amb\Smart_City_Analysis\frontend
npm run dev
```

Vite will display a local URL, typically:

```text
http://localhost:5173
```

Open the displayed URL in a browser.

---

# 21. Model Training

The trained model files are already included in:

```text
models/
```

### Train Energy Model

```powershell
python backend/train_energy_model.py
```

### Test Energy Model

```powershell
python backend/test_energy_model.py
```

### Train Anomaly Model

```powershell
python backend/train_anomaly_model.py
```

Current model files:

```text
models/energy_model.joblib
models/energy_anomaly_model.joblib
```

> Retraining may change the resulting model parameters and predictions. The metrics documented in this README correspond to the current evaluated prototype workflow.

---

# 22. Data Processing

To regenerate processed datasets:

```powershell
python backend/process_data.py
```

Processed files will be written to:

```text
dataset/processed/
```

---

# 23. Exploratory Data Analysis

To regenerate the EDA outputs:

```powershell
python backend/eda.py
```

Generated visualizations are stored under:

```text
outputs/eda/
```

---

# 24. Application Testing

The application was tested across the main workflow.

## Dashboard

Verified:

- Dashboard loads successfully
- Statistics are displayed
- Charts load successfully
- City Intelligence section appears
- Sensor overview loads

## Energy Prediction

Test input:

```text
Voltage: 230
Current: 2.2
Power Factor: 0.95
```

Observed model output:

```text
Approximately 510.36
```

## Energy Anomaly Detection

Normal and deliberately unusual energy readings were submitted to verify:

- API connectivity
- Model inference
- Result display
- Database persistence

## Database Persistence

Prediction and anomaly records were verified after:

- Browser refresh
- Backend restart

## Sensor Modules

The following modules were tested:

- Air Quality
- Traffic
- Weather

## Input Validation

Invalid values such as:

- Negative voltage
- Negative current
- Invalid power factor
- Negative energy usage

were tested and rejected by the application.

## Full End-to-End Workflow

```text
React UI
   ↓
Flask REST API
   ↓
Input Validation
   ↓
ML Model
   ↓
SQLite Database
   ↓
API Response
   ↓
React Visualization
```

---

# 25. Limitations

The current implementation is a working academic prototype and has several limitations.

## Dataset Size

The available datasets are relatively small and cover a limited time period.

## Model Generalization

The energy prediction model has been evaluated using the available dataset and cross-validation, but additional real-world data would be required to establish reliable generalization performance.

## Anomaly Detection

The Isolation Forest model provides potential anomaly flags. These should not be treated as confirmed equipment failures without additional domain-specific validation.

## Real-Time Data

The current application works with prepared sensor datasets rather than a continuously connected live IoT sensor network.

## Production Deployment

The current architecture is suitable for demonstration and academic prototyping. A production system would require additional security, scalability, monitoring, authentication, and infrastructure.

## Dataset Scale

Because only a small number of observations are available, the current dashboard should be considered a demonstration of the complete analytics workflow rather than a statistically representative smart-city monitoring system.

---

# 26. Future Enhancements

Possible future improvements include:

- Real-time IoT sensor integration
- MQTT or Kafka-based streaming
- Larger historical datasets
- Advanced time-series forecasting
- More robust anomaly detection
- Geographic/map-based visualization
- User authentication
- Role-based access control
- Alert and notification system
- Cloud deployment
- Automated model retraining
- Model monitoring and drift detection
- Integration with additional smart-city data sources
- Advanced predictive analytics
- Sensor-health monitoring
- Historical trend comparison
- Configurable anomaly thresholds
- Exportable reports

---

# 27. Security and Production Considerations

For production deployment, the following would be required:

- Secure API authentication
- HTTPS
- Environment-based configuration
- Database access controls
- Input sanitization
- Rate limiting
- Logging and monitoring
- Secure model and dataset storage
- Proper secrets management
- Production-grade database infrastructure
- Backup and recovery mechanisms

The current prototype intentionally keeps the architecture lightweight for development and academic demonstration.

---

# 28. Dataset Attribution

The sensor datasets used in this academic project were obtained/adapted from publicly available dataset resources.

Before public redistribution or commercial deployment, the exact original dataset source, dataset title, author/uploader, and license should be verified from the original source page and credited according to its terms.

The following parts of the application were developed as part of this project:

- React frontend
- Dashboard interface
- Flask backend
- REST API integration
- SQLite database layer
- Data preprocessing pipeline
- Exploratory data analysis workflow
- Machine-learning workflow
- Energy prediction integration
- Anomaly-detection integration
- Interactive visualizations
- Application integration and testing

Do not claim ownership of the original third-party datasets. Follow the applicable dataset license and attribution requirements.

---

# 29. Responsible Interpretation of Results

The machine-learning results in this project should be interpreted within the context of the available dataset.

The reported energy-model metrics are:

```text
MAE: 3.90
R² : 0.780
```

These values were obtained using five-fold cross-validation on a small dataset.

The Isolation Forest exploratory result was:

```text
11 normal observations
19 potential anomaly flags
```

These results demonstrate implementation of the machine-learning workflow but should not be presented as evidence of production-ready accuracy, confirmed fault diagnosis, or city-scale predictive capability.

---

# 30. Conclusion

The **Smart City Urban Analytics Platform** demonstrates how multiple urban sensor datasets can be integrated into a complete full-stack analytics application.

The system combines:

```text
Sensor Data
     +
Data Processing
     +
Exploratory Data Analysis
     +
Machine Learning
     +
Anomaly Detection
     +
Database Persistence
     +
REST APIs
     +
Interactive Visualization
     =
Smart City Urban Analytics Platform
```

The current implementation provides a functional foundation that can be extended toward real-time smart-city monitoring and predictive analytics using larger datasets, live IoT infrastructure, streaming technologies, and production-grade deployment.

---

# 31. Project Information

**Project:** Smart City Urban Analytics Platform

**Type:** Academic Full-Stack + Machine Learning Project

## Core Technologies

- React
- Vite
- Flask
- SQLite
- Pandas
- NumPy
- Scikit-learn
- Joblib
- Matplotlib
- Seaborn
- Recharts

## Primary Analytics Modules

- Energy Prediction
- Energy Anomaly Detection
- Air Quality Monitoring
- Traffic Analytics
- Weather Analytics

---

# 32. Author / Project

**Smart City Urban Analytics Platform**

Academic Full-Stack + Machine Learning Project.

Built using React, Flask, SQLite, Pandas, NumPy and Scikit-learn.

---

## Note

The exact original dataset source information should be added to the **Dataset Attribution** section before public release if the project is distributed outside the academic submission.

No unverified dataset title, uploader, or license information has been invented in this README.