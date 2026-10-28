# API reference

Base path `/api/v1`. All responses are JSON. Timestamps are ISO 8601 and naive (the simulator has no
time zone). Sensor data ends at `2026-04-30T23:00:00`, so "latest" always means the end of the dataset.

## Errors

Every error has the same shape.

```json
{ "error": { "code": "invalid_zone", "message": "zone must be one of: Downtown, Industrial, ..." } }
```

| Status | Meaning | Codes |
|---|---|---|
| 400 | Bad parameter or body | `invalid_zone`, `invalid_parameter`, `invalid_field`, `missing_field`, `invalid_body` |
| 401 | Missing or wrong `X-API-Key` (only when `SMARTCITY_API_KEY` is set) | `unauthorized` |
| 404 | Unknown route, domain or figure | `not_found`, `unknown_domain` |
| 413 | Request body over 64 KB | `request_entity_too_large` |
| 429 | Too many POST requests from one client | `rate_limited` |
| 422 | Valid input the data cannot serve | `origin_out_of_range`, `insufficient_history`, `unknown_zone_profile` |
| 503 | Not ready | `model_unavailable`, `metrics_unavailable`, `no_data` |
| 500 | Unexpected (logged server-side) | `internal_error` |

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Readiness: database, models, data range. Returns 503 until models exist |
| GET | `/zones` | Zone names, codes and types |
| GET | `/overview?zone=` | 24-hour KPIs with change vs the previous 24 hours, per-zone table, sensor health, forecast accuracy |
| GET | `/series/{domain}` | Readings. Domains: `energy`, `traffic`, `air-quality`, `weather` |
| GET | `/series/{domain}/summary` | Mean, min, max and missing share per measure |
| GET | `/series/{domain}/profile` | Mean by hour of day, weekday vs weekend |
| POST | `/energy/forecast` | Demand forecast with a 90% interval |
| POST | `/energy/anomaly` | Score one reading, with reasons |
| GET | `/energy/anomalies` | Flagged historical readings |
| GET | `/predictions` | Audit log of forecast and anomaly requests |
| GET | `/models/metrics` | Full evaluation report (drives the Model performance page) |
| GET | `/models/figures/{name}.png` | Rendered evaluation figures |

### `GET /series/{domain}`

| Parameter | Default | Notes |
|---|---|---|
| `zone` | `all` | A zone name or `all` (long format, one row per zone and time) |
| `resolution` | `hourly` | `daily` sums energy, traffic and rain, and averages everything else |
| `start`, `end` | last 7 days hourly, 60 days daily | ISO 8601 |
| `limit`, `offset` | 5000, 0 | `limit` is capped at 20,000; the response includes `total` |

Hourly records include `status`. Missing measurements are `null`.

### `POST /energy/forecast`

```json
{
  "zone": "Residential",
  "horizon_hours": 24,
  "origin": "2026-04-30T23:00:00",
  "weather": { "temperature_c": -5, "precipitation_mm": 0 }
}
```

`horizon_hours` is `1` or `24`. `origin` defaults to the latest reading and must leave at least 8 days of
history before it. `weather` is optional and overrides the weather assumed for the target hour; without
it the previous day's same-hour weather is used.

```json
{
  "zone": "Residential",
  "horizon_hours": 24,
  "origin": "2026-04-30T23:00:00",
  "target_time": "2026-05-01T23:00:00",
  "forecast_kwh": 266.9,
  "interval": {
    "lower": 217.19,
    "upper": 316.62,
    "coverage": 0.9
  },
  "model": "Random forest",
  "inputs": {
    "latest_observed_kwh": 265.525,
    "same_hour_last_week_kwh": 256.713,
    "assumed_weather": {
      "temperature_c": -5.0,
      "humidity_pct": 75.746,
      "wind_speed_ms": 5.852,
      "precipitation_mm": 0.0
    },
    "weather_overridden": [
      "precipitation_mm",
      "temperature_c"
    ]
  },
  "record_id": 2
}
```

### `POST /energy/anomaly`

```json
{
  "zone": "Downtown",
  "timestamp": "2026-04-14T13:00:00",
  "energy_kwh": 700,
  "voltage_v": 400,
  "current_a": 668,
  "power_factor": 0.95
}
```

Ranges: `energy_kwh` 0 to 1e6, `voltage_v` 0 to 1e5, `current_a` 0 to 1e6, `power_factor` 0 to 1. Response:

```json
{
  "zone": "Downtown",
  "timestamp": "2026-04-14T13:00:00",
  "anomaly": true,
  "classification": "Anomalous",
  "score": 0.6778,
  "threshold": 0.6168,
  "expected_kwh": 451.69,
  "reasons": [
    "Demand is 1.5x the typical level for this hour",
    "Metered energy disagrees with V x I x pf by 37% (possible meter fault)"
  ],
  "signals": {
    "profile_z": 10.1467,
    "log_ratio": 0.4342,
    "power_balance": -0.3693,
    "voltage_dev": 0.0,
    "power_factor": 0.95
  },
  "record_id": 7
}
```

### `GET /energy/anomalies`

`zone`, `start`, `end` (default last 30 days), `flagged` (`true` by default, `false` lists everything),
`limit` (default 50, max 500), `offset`. Each record includes the electrical readings, the detector's
`reasons`, and `true_type`, the simulator's ground truth, which exists only because the data is simulated.

## Quick check

```bash
curl -s localhost:5000/api/v1/health
curl -s "localhost:5000/api/v1/series/weather?zone=Harbor&resolution=daily&limit=3"
curl -s -X POST localhost:5000/api/v1/energy/forecast \
     -H 'content-type: application/json' -d '{"zone":"Harbor","horizon_hours":24}'
```
