# Data card

## Provenance

The dataset is **simulated**. No public dataset covers weather, traffic, air quality and substation
telemetry for the same zones and hours, and a platform that links those domains needs exactly that.
`backend/smartcity/simulate.py` generates it from a fixed seed (`2026`), so every run reproduces the
same files. Treat every number in this repository as a property of the simulator, not of any real city.

| | |
|---|---|
| Period | 2026-01-01 00:00 to 2026-04-30 23:00 (120 days, hourly) |
| Zones | Downtown, Industrial, Residential, Harbor, University |
| Rows | 14,400 per network (5 zones x 2,880 hours), 57,600 sensor readings in total |
| Anomaly labels | 453 labelled hours across 4 fault types, in a separate file |

## Files

| File | Columns |
|---|---|
| `dataset/energy.csv` | `timestamp, zone, device_id, energy_kwh, voltage_v, current_a, power_factor, status` |
| `dataset/traffic.csv` | `timestamp, zone, device_id, traffic_count, avg_speed_kmh, status` |
| `dataset/air_quality.csv` | `timestamp, zone, device_id, pm25_ugm3, pm10_ugm3, co2_ppm, no2_ppb, status` |
| `dataset/weather.csv` | `timestamp, zone, device_id, temperature_c, humidity_pct, wind_speed_ms, precipitation_mm, status` |
| `dataset/energy_anomaly_labels.csv` | `timestamp, zone, anomaly_type` (simulator ground truth, used only for evaluation) |

`status` is `OK`, `DEGRADED` (readings carry extra noise) or `OFFLINE` (all measurements missing).

## Relationships encoded

These are what make the cross-domain analysis meaningful:

- **Weather to energy.** Heating demand rises as temperature falls below 14 C. Rain adds a small load.
- **Calendar to energy and traffic.** Each zone type (commercial, industrial, residential, harbor, campus)
  has its own weekday and weekend profile. Traffic has morning and evening peaks on weekdays and a single
  midday hump at weekends.
- **Traffic to air quality.** PM2.5, NO2 and CO2 rise with vehicle counts, scaled by each zone's emission
  factor. Industrial shifts add a particulate source.
- **Weather to air quality.** Wind disperses particulates, rain washes them out, and calm nights trap them.
- **Traffic to weather.** Rain suppresses traffic and lowers average speed.
- **Electrical consistency.** Current is derived from three-phase power, `I = P / (sqrt(3) V pf)`, with
  measurement noise, so healthy readings satisfy that identity to within a few percent.

## Faults and data quality

Sensor reliability problems (1.6% to 1.9% of readings in each network are `DEGRADED` or `OFFLINE`, and about 1.4% to 1.6% of measurement cells are missing):

- scattered single missing values,
- `DEGRADED` stretches of 2 to 8 hours with 6% extra noise,
- `OFFLINE` gaps of 2 to 12 hours.

Labelled grid anomalies (only in the energy network, never hidden by an outage):

| Type | What happens | Visible in |
|---|---|---|
| `spike` | true demand rises 1.3x to 2.1x for 1 to 3 hours | energy vs typical profile |
| `outage` | demand collapses to 0 to 30% for 2 to 7 hours | energy vs typical profile |
| `meter_fault` | reported energy is scaled by 0.55 to 0.85 or 1.15 to 1.6 for 6 to 19 hours, while voltage and current stay physical | disagreement between metered energy and V x I x pf |
| `voltage_sag` | voltage drops 10 to 22% for 1 to 3 hours, current rises to compensate | voltage only |

## Regenerating

```bash
smartcity simulate --days 120 --seed 2026   # rewrites dataset/*.csv
smartcity ingest                            # reload SQLite
smartcity train                             # retrain, rewrite metrics and figures
```

## Using real data

The pipeline reads the same five CSVs whatever produced them, so real sensor exports can replace the
simulated ones. What it requires:

- **Schema.** The columns listed above, with ISO timestamps (`YYYY-MM-DD HH:MM:SS`), one row per zone and
  hour per network. Missing readings should be empty cells; unhealthy sensors should carry
  `status = DEGRADED` or `OFFLINE`.
- **Hourly cadence.** Features such as the 24-hour and weekly lags assume one reading per hour. Resample
  sub-hourly data before ingesting.
- **At least about 6 weeks per zone.** One week is consumed by the weekly lag and 28 days are held out
  for evaluation.
- **Zone names.** The five zones are defined in `ZONES` in `backend/smartcity/config.py`. They drive the
  one-hot features, API validation and the dashboard selector, so a different city needs that list (and
  the matching list in `frontend/src/lib/measures.js`) updated. The `PROFILES` in `simulate.py` are used
  only for simulation and can be ignored.
- **Anomaly labels (not yet optional).** `smartcity train` scores the anomaly detector against
  `energy_anomaly_labels.csv` and fails without positive examples. Running on real data that has no
  ground truth needs a small change to skip that benchmark and the pages that display it; it has not been
  built or tested.

```bash
cp my_energy.csv dataset/energy.csv   # and traffic, air_quality, weather
smartcity ingest && smartcity train
```
