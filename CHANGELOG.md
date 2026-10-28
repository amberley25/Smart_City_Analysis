# Changelog

## 1.0.0

A rebuild of the original prototype.

### Data
- Replaced four hand-written CSVs of 34 to 49 rows with a seeded simulator: 120 days, hourly, five zones,
  57,600 readings with cross-domain relationships, sensor faults and labelled grid anomalies.
- Reproducible dataset generation (`smartcity simulate`).

### Machine learning
- The energy model no longer predicts a quantity that is a near-formula of its inputs. It now forecasts
  demand 1 and 24 hours ahead from lagged demand, calendar and weather, with no information from after the
  forecast origin (enforced by a test).
- Chronological holdout, expanding-window cross-validation, naive baselines, prediction intervals.
- Anomaly detection redesigned around profile deviation and electrical consistency, benchmarked against
  labelled faults and against the original approach, with a voltage-limit rule for deep sags and an ablation showing what that rule contributes.
- Evaluation charts generated for every model (`docs/figures/`).

### Backend
- Package layout with an application factory, configuration from the environment and a CLI.
- SQLite schema for all four networks, anomaly flags and a prediction audit log.
- Versioned API with validation, pagination, structured errors and model hot-reload.
- 75 backend tests and 23 frontend tests.

### Frontend
- Rebuilt as a routed, componentised dashboard: overview, energy, environment, mobility and model
  performance, with a forecast what-if tool and an anomaly checker.

### Security
- Optional API key, per-client rate limit on POST endpoints, 64 KB body cap, restrictive CORS default and
  safe response headers.

### Delivery
- Docker and Compose, a Makefile, GitHub Actions CI, linting and formatting, project documentation.
