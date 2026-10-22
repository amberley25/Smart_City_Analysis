"""HTTP routes for the v1 API."""

from __future__ import annotations

import json
import math

import pandas as pd
from flask import Blueprint, current_app, jsonify, request, send_from_directory

from .. import __version__, db
from ..config import ZONES
from ..features import HORIZONS, WEATHER
from . import services
from .services import ApiError

bp = Blueprint("api", __name__, url_prefix="/api/v1")

DOMAIN_SLUGS = {"energy": "energy", "traffic": "traffic", "air-quality": "air_quality", "weather": "weather"}
MAX_LIMIT = 20_000
WEATHER_LIMITS = {
    "temperature_c": (-40, 50),
    "humidity_pct": (0, 100),
    "wind_speed_ms": (0, 60),
    "precipitation_mm": (0, 200),
}
READING_LIMITS = {
    "energy_kwh": (0, 1e6),
    "voltage_v": (0, 1e5),
    "current_a": (0, 1e6),
    "power_factor": (0, 1.0),
}


def _settings():
    return current_app.config["SETTINGS"]


def _store():
    return current_app.config["MODEL_STORE"]


# ---------------------------------------------------------------------------
# Request parsing
# ---------------------------------------------------------------------------


def _zone(value: str | None, allow_all: bool = True) -> str:
    value = value or ("all" if allow_all else None)
    if value == "all" and allow_all:
        return value
    if value not in ZONES:
        raise ApiError(400, "invalid_zone", f"zone must be one of: {', '.join(ZONES)}" + (", all" if allow_all else ""))
    return value


def _int(name: str, default: int, low: int, high: int) -> int:
    raw = request.args.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ApiError(400, "invalid_parameter", f"{name} must be an integer") from None
    if not low <= value <= high:
        raise ApiError(400, "invalid_parameter", f"{name} must be between {low} and {high}")
    return value


def _timestamp(name: str) -> pd.Timestamp | None:
    raw = request.args.get(name)
    if raw is None:
        return None
    return _parse_time(raw, name)


def _parse_time(raw, name: str) -> pd.Timestamp:
    try:
        stamp = pd.Timestamp(raw)
    except (ValueError, TypeError):
        raise ApiError(400, "invalid_parameter", f"{name} must be an ISO 8601 timestamp") from None
    if pd.isna(stamp):
        raise ApiError(400, "invalid_parameter", f"{name} must be an ISO 8601 timestamp")
    return stamp.tz_convert(None) if stamp.tzinfo else stamp


def _window(default_days: int) -> tuple[pd.Timestamp, pd.Timestamp]:
    _, last = services.data_bounds(_settings())
    end = _timestamp("end") or last
    start = _timestamp("start") or end - pd.Timedelta(days=default_days)
    if start > end:
        raise ApiError(400, "invalid_parameter", "start must not be after end")
    return start, end


def _body() -> dict:
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_body", "A JSON object body is required")
    return data


def _number(data: dict, name: str, low: float, high: float, required: bool = True) -> float | None:
    if data.get(name) is None:
        if required:
            raise ApiError(400, "missing_field", f"{name} is required")
        return None
    value = data[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApiError(400, "invalid_field", f"{name} must be a number")
    if not math.isfinite(value) or not low <= value <= high:
        raise ApiError(400, "invalid_field", f"{name} must be between {low:g} and {high:g}")
    return float(value)


# ---------------------------------------------------------------------------
# Operational
# ---------------------------------------------------------------------------


@bp.get("/health")
def health():
    try:
        first, last = services.data_bounds(_settings())
        data = {"first": first.isoformat(), "last": last.isoformat()}
        database = "ok"
    except ApiError:
        data, database = None, "empty"
    models = _store().available()
    ready = database == "ok" and all(models.values())
    return jsonify(
        {
            "status": "ok" if ready else "degraded",
            "version": __version__,
            "database": database,
            "models": models,
            "data_range": data,
        }
    ), 200 if ready else 503


@bp.get("/zones")
def zones():
    return jsonify({"zones": services.zone_directory()})


@bp.get("/overview")
def overview():
    zone = _zone(request.args.get("zone"))
    return jsonify(services.overview(_settings(), zone, _load_metrics(optional=True)))


# ---------------------------------------------------------------------------
# Sensor series
# ---------------------------------------------------------------------------


def _series_domain(slug: str) -> str:
    if slug not in DOMAIN_SLUGS:
        raise ApiError(404, "unknown_domain", f"domain must be one of: {', '.join(DOMAIN_SLUGS)}")
    return DOMAIN_SLUGS[slug]


@bp.get("/series/<slug>")
def series(slug: str):
    domain = _series_domain(slug)
    zone = _zone(request.args.get("zone"))
    resolution = request.args.get("resolution", "hourly")
    if resolution not in ("hourly", "daily"):
        raise ApiError(400, "invalid_parameter", "resolution must be hourly or daily")
    start, end = _window(default_days=7 if resolution == "hourly" else 60)
    if resolution == "daily" and _timestamp("start") is None:
        start = start.ceil("D")
    limit = _int("limit", 5000, 1, MAX_LIMIT)
    offset = _int("offset", 0, 0, 10**7)
    records, total = services.query_series(_settings(), domain, zone, start, end, resolution, limit, offset)
    return jsonify(
        {
            "domain": domain,
            "zone": zone,
            "resolution": resolution,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "measures": db.MEASURES[domain],
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": records,
        }
    )


@bp.get("/series/<slug>/summary")
def series_summary(slug: str):
    domain = _series_domain(slug)
    zone = _zone(request.args.get("zone"))
    start, end = _window(default_days=30)
    return jsonify(
        {
            "domain": domain,
            "zone": zone,
            "start": start.isoformat(),
            "end": end.isoformat(),
            **services.series_summary(_settings(), domain, zone, start, end),
        }
    )


@bp.get("/series/<slug>/profile")
def series_profile(slug: str):
    domain = _series_domain(slug)
    zone = _zone(request.args.get("zone"))
    return jsonify(
        {
            "domain": domain,
            "zone": zone,
            "measure": db.PRIMARY_MEASURE[domain],
            "profile": services.hourly_profile(_settings(), domain, zone),
        }
    )


# ---------------------------------------------------------------------------
# Energy intelligence
# ---------------------------------------------------------------------------


@bp.post("/energy/forecast")
def energy_forecast():
    data = _body()
    zone = _zone(data.get("zone"), allow_all=False)
    horizon = data.get("horizon_hours", 1)
    if horizon not in HORIZONS:
        raise ApiError(400, "invalid_field", f"horizon_hours must be one of {list(HORIZONS)}")
    origin = _parse_time(data["origin"], "origin") if data.get("origin") else None
    overrides = {}
    for column in WEATHER:
        value = _number(data.get("weather") or {}, column, *WEATHER_LIMITS[column], required=False)
        if value is not None:
            overrides[column] = value
    result = services.forecast(_settings(), _store(), zone, horizon, origin, overrides)
    result["record_id"] = services.log_prediction(_settings(), "forecast", zone, result["target_time"], data, result)
    return jsonify(result)


@bp.post("/energy/anomaly")
def energy_anomaly():
    data = _body()
    zone = _zone(data.get("zone"), allow_all=False)
    if not data.get("timestamp"):
        raise ApiError(400, "missing_field", "timestamp is required")
    stamp = _parse_time(data["timestamp"], "timestamp")
    reading = {name: _number(data, name, *limits) for name, limits in READING_LIMITS.items()}
    reading.update(zone=zone, timestamp=stamp)
    result = services.score_reading(_store(), reading)
    result["timestamp"] = stamp.isoformat()
    result["record_id"] = services.log_prediction(_settings(), "anomaly", zone, stamp.isoformat(), data, result)
    return jsonify(result)


@bp.get("/energy/anomalies")
def energy_anomalies():
    zone = _zone(request.args.get("zone"))
    start, end = _window(default_days=30)
    flagged = request.args.get("flagged", "true").lower() != "false"
    limit, offset = _int("limit", 50, 1, 500), _int("offset", 0, 0, 10**7)
    records, total = services.list_anomalies(_settings(), zone, flagged, start, end, limit, offset)
    return jsonify(
        {
            "zone": zone,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "total": total,
            "limit": limit,
            "offset": offset,
            "records": records,
        }
    )


@bp.get("/predictions")
def predictions():
    kind = request.args.get("kind")
    if kind not in (None, "forecast", "anomaly"):
        raise ApiError(400, "invalid_parameter", "kind must be forecast or anomaly")
    limit, offset = _int("limit", 25, 1, 200), _int("offset", 0, 0, 10**7)
    records, total = services.prediction_history(_settings(), kind, limit, offset)
    return jsonify({"total": total, "limit": limit, "offset": offset, "records": records})


# ---------------------------------------------------------------------------
# Model evaluation
# ---------------------------------------------------------------------------


def _load_metrics(optional: bool = False) -> dict | None:
    path = _settings().metrics_path
    if not path.exists():
        if optional:
            return None
        raise ApiError(503, "metrics_unavailable", "No evaluation report found; run `smartcity train` first")
    return json.loads(path.read_text())


@bp.get("/models/metrics")
def model_metrics():
    return jsonify(_load_metrics())


@bp.get("/models/figures/<name>")
def model_figure(name: str):
    if not name.endswith(".png"):
        raise ApiError(404, "not_found", "Figure not found")
    return send_from_directory(_settings().figure_dir, name, max_age=3600)
