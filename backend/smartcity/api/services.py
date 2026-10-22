"""Business logic behind the HTTP layer: querying, forecasting and anomaly scoring."""

from __future__ import annotations

import json
import threading
from datetime import timedelta

import joblib
import numpy as np
import pandas as pd

from .. import anomaly, db
from ..config import ZONES, Settings
from ..features import HORIZONS, WEATHER, make_forecast_frame
from ..simulate import PROFILES

HISTORY_HOURS = 24 * 8 + 6


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def clean_records(frame: pd.DataFrame) -> list[dict]:
    return frame.astype(object).where(frame.notna(), None).to_dict("records")


class ModelStore:
    """Lazily loads trained artefacts and reloads them when the files change."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._lock = threading.Lock()
        self._cache: dict[str, tuple[float, object]] = {}

    def _load(self, filename: str):
        path = self.settings.model_dir / filename
        if not path.exists():
            raise ApiError(503, "model_unavailable", f"{filename} not found; run `smartcity train` first")
        mtime = path.stat().st_mtime
        with self._lock:
            cached = self._cache.get(filename)
            if cached is None or cached[0] != mtime:
                cached = (mtime, joblib.load(path))
                self._cache[filename] = cached
            return cached[1]

    def forecaster(self, horizon: int) -> dict:
        return self._load(f"forecast_h{horizon}.joblib")

    def detector(self) -> dict:
        return self._load("anomaly_detector.joblib")

    def available(self) -> dict[str, bool]:
        names = [f"forecast_h{h}.joblib" for h in HORIZONS] + ["anomaly_detector.joblib"]
        return {n.removesuffix(".joblib"): (self.settings.model_dir / n).exists() for n in names}


# ---------------------------------------------------------------------------
# Time-series access
# ---------------------------------------------------------------------------


def data_bounds(settings: Settings) -> tuple[pd.Timestamp, pd.Timestamp]:
    with db.session(settings) as conn:
        row = conn.execute("SELECT MIN(timestamp), MAX(timestamp) FROM energy").fetchone()
    if row[0] is None:
        raise ApiError(503, "no_data", "The database is empty; run `smartcity ingest` first")
    return pd.Timestamp(row[0]), pd.Timestamp(row[1])


def query_series(
    settings: Settings, domain: str, zone: str, start, end, resolution: str, limit: int, offset: int
) -> tuple[list[dict], int]:
    measures = db.MEASURES[domain]
    where, params = ["timestamp >= ?", "timestamp <= ?"], [start.isoformat(), end.isoformat()]
    if zone != "all":
        where.append("zone = ?")
        params.append(zone)
    clause = " AND ".join(where)

    if resolution == "daily":
        columns = ", ".join(f"ROUND({db.DAILY_AGG[m]}({m}), 3) AS {m}" for m in measures)
        base = (
            f"SELECT date(timestamp) AS timestamp, zone, {columns} FROM {domain} "
            f"WHERE {clause} GROUP BY date(timestamp), zone"
        )
    else:
        base = f"SELECT timestamp, zone, {', '.join(measures)}, status FROM {domain} WHERE {clause}"

    with db.session(settings) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM ({base})", params).fetchone()[0]
        rows = conn.execute(f"{base} ORDER BY timestamp, zone LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
    return [dict(r) for r in rows], int(total)


def series_summary(settings: Settings, domain: str, zone: str, start, end) -> dict:
    measures = db.MEASURES[domain]
    where, params = ["timestamp >= ?", "timestamp <= ?"], [start.isoformat(), end.isoformat()]
    if zone != "all":
        where.append("zone = ?")
        params.append(zone)
    parts = []
    for m in measures:
        parts += [f"AVG({m})", f"MIN({m})", f"MAX({m})", f"SUM({m} IS NULL)"]
    sql = f"SELECT COUNT(*), {', '.join(parts)} FROM {domain} WHERE {' AND '.join(where)}"
    with db.session(settings) as conn:
        row = conn.execute(sql, params).fetchone()
    count, out = row[0], {}
    for i, m in enumerate(measures):
        mean, low, high, missing = row[1 + 4 * i : 5 + 4 * i]
        out[m] = {
            "mean": None if mean is None else round(mean, 3),
            "min": low,
            "max": high,
            "missing_pct": round(100 * (missing or 0) / count, 2) if count else 0.0,
        }
    return {"rows": count, "measures": out}


def hourly_profile(settings: Settings, domain: str, zone: str) -> list[dict]:
    measure = db.PRIMARY_MEASURE[domain]
    where, params = "", []
    if zone != "all":
        where, params = "WHERE zone = ?", [zone]
    sql = f"""
        SELECT CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
               CASE WHEN strftime('%w', timestamp) IN ('0', '6') THEN 'weekend' ELSE 'weekday' END AS daytype,
               AVG({measure}) AS value
        FROM {domain} {where} GROUP BY hour, daytype ORDER BY hour"""
    with db.session(settings) as conn:
        rows = conn.execute(sql, params).fetchall()
    table: dict[int, dict] = {h: {"hour": h, "weekday": None, "weekend": None} for h in range(24)}
    for r in rows:
        table[r["hour"]][r["daytype"]] = None if r["value"] is None else round(r["value"], 3)
    return list(table.values())


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------


def _change(current, previous) -> dict:
    pct = None if not previous else round(100 * (current - previous) / previous, 1)
    return {
        "value": None if current is None else round(current, 2),
        "previous": None if previous is None else round(previous, 2),
        "change_pct": pct,
    }


def overview(settings: Settings, zone: str, metrics: dict | None) -> dict:
    _, as_of = data_bounds(settings)
    zone_clause, zone_params = ("AND zone = ?", [zone]) if zone != "all" else ("", [])

    def window(domain: str, expr: str, lo: pd.Timestamp, hi: pd.Timestamp):
        sql = f"SELECT {expr} FROM {domain} WHERE timestamp > ? AND timestamp <= ? {zone_clause}"
        with db.session(settings) as conn:
            return conn.execute(sql, [lo.isoformat(), hi.isoformat(), *zone_params]).fetchone()[0]

    cur = (as_of - timedelta(hours=24), as_of)
    prev = (as_of - timedelta(hours=48), as_of - timedelta(hours=24))
    spec = {
        "energy_kwh": ("energy", "SUM(energy_kwh)"),
        "traffic_count": ("traffic", "AVG(traffic_count)"),
        "pm25_ugm3": ("air_quality", "AVG(pm25_ugm3)"),
        "temperature_c": ("weather", "AVG(temperature_c)"),
        "precipitation_mm": ("weather", "SUM(precipitation_mm)"),
    }
    kpis = {k: _change(window(d, e, *cur), window(d, e, *prev)) for k, (d, e) in spec.items()}

    with db.session(settings) as conn:
        flagged = {
            label: conn.execute(
                f"SELECT COUNT(*) FROM energy_anomalies WHERE flagged = 1 AND timestamp > ? {zone_clause}",
                [(as_of - timedelta(hours=hours)).isoformat(), *zone_params],
            ).fetchone()[0]
            for label, hours in (("last_24h", 24), ("last_7d", 24 * 7))
        }
        per_zone = []
        for z in ZONES:
            args = [(as_of - timedelta(hours=24)).isoformat(), as_of.isoformat(), z]

            def one(domain, expr, a=args):
                return conn.execute(
                    f"SELECT {expr} FROM {domain} WHERE timestamp > ? AND timestamp <= ? AND zone = ?", a
                ).fetchone()[0]

            per_zone.append(
                {
                    "zone": z,
                    "energy_kwh": one("energy", "ROUND(SUM(energy_kwh), 1)"),
                    "traffic_count": one("traffic", "ROUND(AVG(traffic_count), 0)"),
                    "pm25_ugm3": one("air_quality", "ROUND(AVG(pm25_ugm3), 1)"),
                    "temperature_c": one("weather", "ROUND(AVG(temperature_c), 1)"),
                    "flagged_7d": conn.execute(
                        "SELECT COUNT(*) FROM energy_anomalies WHERE flagged = 1 AND zone = ? AND timestamp > ?",
                        [z, (as_of - timedelta(days=7)).isoformat()],
                    ).fetchone()[0],
                }
            )
        health = {}
        for domain in db.MEASURES:
            counts = {
                r[0]: r[1]
                for r in conn.execute(
                    f"SELECT status, COUNT(*) FROM {domain} WHERE timestamp > ? {zone_clause} GROUP BY status",
                    [(as_of - timedelta(days=7)).isoformat(), *zone_params],
                )
            }
            total = sum(counts.values()) or 1
            health[domain] = {s: round(100 * counts.get(s, 0) / total, 2) for s in ("OK", "DEGRADED", "OFFLINE")}

    accuracy = None
    if metrics:
        h1 = metrics["forecast"]["1"]
        best = next(m for m in h1["models"] if m["name"] == h1["best_model"])
        base = next(m for m in h1["models"] if m["name"] == "Persistence")
        accuracy = {
            "model": h1["best_model"],
            "mae": best["test_mae"],
            "r2": best["test_r2"],
            "baseline_mae": base["test_mae"],
            "improvement_pct": h1["improvement_vs_best_baseline_pct"],
        }
    return {
        "as_of": as_of.isoformat(),
        "zone": zone,
        "window_hours": 24,
        "kpis": kpis,
        "anomalies": flagged,
        "zones": per_zone,
        "sensor_health": health,
        "forecast_accuracy": accuracy,
    }


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------


def _window_panel(
    settings: Settings, zone: str, origin: pd.Timestamp, horizon: int, overrides: dict[str, float]
) -> pd.DataFrame:
    start = origin - timedelta(hours=HISTORY_HOURS)
    target = origin + timedelta(hours=horizon)
    index = pd.date_range(start, target, freq="h", name="timestamp")
    panel = pd.DataFrame(index=index)

    with db.session(settings) as conn:

        def pull(domain, columns):
            sql = f"SELECT timestamp, {', '.join(columns)} FROM {domain} WHERE zone = ? AND timestamp BETWEEN ? AND ?"
            frame = pd.read_sql_query(sql, conn, params=[zone, start.isoformat(), target.isoformat()])
            frame["timestamp"] = pd.to_datetime(frame["timestamp"])
            return frame.set_index("timestamp")

        energy, traffic, weather = (
            pull("energy", ["energy_kwh"]),
            pull("traffic", ["traffic_count"]),
            pull("weather", WEATHER),
        )

    panel = panel.join(energy).join(traffic).join(weather)
    future = panel.index > origin
    panel.loc[future, ["energy_kwh", "traffic_count"]] = np.nan
    if horizon > 0:
        # No observed weather beyond the origin: carry the same hour of the previous day forward.
        for column in WEATHER:
            missing = panel[column].isna() & future
            panel.loc[missing, column] = panel[column].shift(24)[missing]
    for column, value in overrides.items():
        panel.loc[target, column] = value
    panel.insert(0, "zone", zone)
    return panel.reset_index()


def forecast(
    settings: Settings,
    store: ModelStore,
    zone: str,
    horizon: int,
    origin: pd.Timestamp | None,
    overrides: dict[str, float],
) -> dict:
    first, last = data_bounds(settings)
    origin = last if origin is None else origin.floor("h")
    if origin < first + timedelta(hours=HISTORY_HOURS) or origin > last:
        raise ApiError(
            422,
            "origin_out_of_range",
            f"origin must lie between {(first + timedelta(hours=HISTORY_HOURS)).isoformat()} and {last.isoformat()}",
        )

    bundle = store.forecaster(horizon)
    panel = _window_panel(settings, zone, origin, horizon, overrides)
    frame = make_forecast_frame(panel, horizon, with_target=False)
    row = frame[frame["origin"] == origin]
    if row.empty:
        raise ApiError(422, "insufficient_history", "Not enough sensor history before the requested origin")

    X = row[bundle["features"]]
    if X["energy_now"].isna().all():
        raise ApiError(422, "insufficient_history", "No recent energy reading is available for this zone")
    point = float(bundle["model"].predict(X)[0])
    half = float(bundle["halfwidth"][zone])
    lower, upper = max(point - half, 0.0), point + half
    target = origin + timedelta(hours=horizon)

    last_week = row["same_hour_last_week"].iloc[0]
    result = {
        "zone": zone,
        "horizon_hours": horizon,
        "origin": origin.isoformat(),
        "target_time": target.isoformat(),
        "forecast_kwh": round(point, 2),
        "interval": {"lower": round(lower, 2), "upper": round(upper, 2), "coverage": bundle["coverage"]},
        "model": bundle["name"],
        "inputs": {
            "latest_observed_kwh": _num(row["energy_now"].iloc[0]),
            "same_hour_last_week_kwh": _num(last_week),
            "assumed_weather": {c: _num(row[f"target_{c}"].iloc[0]) for c in WEATHER},
            "weather_overridden": sorted(overrides),
        },
    }
    return result


def _num(value) -> float | None:
    return None if value is None or pd.isna(value) else round(float(value), 3)


# ---------------------------------------------------------------------------
# Anomaly scoring
# ---------------------------------------------------------------------------


def score_reading(store: ModelStore, reading: dict) -> dict:
    bundle = store.detector()
    frame = pd.DataFrame([reading])
    features = anomaly.engineer(frame, bundle["stats"])
    median, _ = bundle["stats"].lookup(frame)
    if np.isnan(median[0]):
        raise ApiError(422, "unknown_zone_profile", "No baseline profile exists for this zone and time")
    score = float(anomaly.anomaly_score(bundle["detector"], features)[0])
    flagged = score >= bundle["threshold"]
    row = features.iloc[0].to_dict()
    return {
        "zone": reading["zone"],
        "timestamp": reading["timestamp"],
        "anomaly": bool(flagged),
        "classification": "Anomalous" if flagged else "Normal",
        "score": round(score, 4),
        "threshold": round(bundle["threshold"], 4),
        "expected_kwh": round(float(median[0]), 2),
        "reasons": anomaly.explain(row) if flagged else [],
        "signals": {k: round(float(v), 4) for k, v in row.items()},
    }


def list_anomalies(settings: Settings, zone: str, flagged_only: bool, start, end, limit: int, offset: int):
    where, params = ["a.timestamp >= ?", "a.timestamp <= ?"], [start.isoformat(), end.isoformat()]
    if zone != "all":
        where.append("a.zone = ?")
        params.append(zone)
    if flagged_only:
        where.append("a.flagged = 1")
    clause = " AND ".join(where)
    with db.session(settings) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM energy_anomalies a WHERE {clause}", params).fetchone()[0]
        rows = conn.execute(
            f"""SELECT a.timestamp, a.zone, a.score, a.flagged, a.reasons, a.true_type,
                       e.energy_kwh, e.voltage_v, e.current_a, e.power_factor
                FROM energy_anomalies a JOIN energy e ON e.zone = a.zone AND e.timestamp = a.timestamp
                WHERE {clause} ORDER BY a.timestamp DESC, a.zone LIMIT ? OFFSET ?""",
            [*params, limit, offset],
        ).fetchall()
    records = []
    for r in rows:
        item = dict(r)
        item["flagged"] = bool(item["flagged"])
        item["reasons"] = json.loads(item["reasons"]) if item["reasons"] else []
        records.append(item)
    return records, int(total)


def log_prediction(
    settings: Settings, kind: str, zone: str, target_time: str | None, request: dict, response: dict
) -> int:
    with db.session(settings) as conn:
        cur = conn.execute(
            "INSERT INTO prediction_log (kind, zone, target_time, request, response) VALUES (?, ?, ?, ?, ?)",
            [kind, zone, target_time, json.dumps(request), json.dumps(response)],
        )
        return int(cur.lastrowid)


def prediction_history(settings: Settings, kind: str | None, limit: int, offset: int):
    where, params = ("WHERE kind = ?", [kind]) if kind else ("", [])
    with db.session(settings) as conn:
        total = conn.execute(f"SELECT COUNT(*) FROM prediction_log {where}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM prediction_log {where} ORDER BY id DESC LIMIT ? OFFSET ?", [*params, limit, offset]
        ).fetchall()
    records = []
    for r in rows:
        item = dict(r)
        item["request"], item["response"] = json.loads(item["request"]), json.loads(item["response"])
        records.append(item)
    return records, int(total)


def zone_directory() -> list[dict]:
    return [{"name": z, "code": PROFILES[z].code, "kind": PROFILES[z].kind} for z in ZONES]
