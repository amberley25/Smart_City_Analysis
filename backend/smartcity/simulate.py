"""Synthetic city sensor network.

No public dataset covers weather, traffic, air quality and substation telemetry for the same
zones and hours, so the platform ships with a seeded simulator. It encodes the relationships a
real network exhibits (heating load follows temperature, traffic follows commuting patterns,
particulates follow traffic and wind) and injects sensor faults and labelled grid anomalies so
detectors can be scored against ground truth.

Everything is deterministic for a given seed.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .config import ZONES, Settings

NOMINAL_VOLTAGE = 400.0  # line-to-line, substation secondary


@dataclass(frozen=True)
class ZoneProfile:
    code: str
    kind: str  # residential | commercial | industrial | harbor | campus
    base_kw: float  # mean substation demand
    traffic_cap: float  # vehicles / hour at saturation
    traffic_scale: float
    emission_factor: float  # relative particulate / NO2 source strength
    temp_offset: float
    wind_offset: float


PROFILES: dict[str, ZoneProfile] = {
    "Downtown": ZoneProfile("DTN", "commercial", 380, 2600, 1.00, 1.15, 0.8, -0.8),
    "Industrial": ZoneProfile("IND", "industrial", 650, 1800, 0.70, 1.90, 0.2, 0.3),
    "Residential": ZoneProfile("RES", "residential", 300, 1500, 0.55, 0.65, 0.0, -0.3),
    "Harbor": ZoneProfile("HBR", "harbor", 240, 1400, 0.45, 1.35, -1.1, 2.1),
    "University": ZoneProfile("UNI", "campus", 210, 1700, 0.60, 0.70, 0.3, -0.2),
}


def _ar1(rng: np.random.Generator, n: int, phi: float, sigma: float) -> np.ndarray:
    noise = rng.normal(0.0, sigma, n)
    out = np.empty(n)
    out[0] = noise[0]
    for i in range(1, n):
        out[i] = phi * out[i - 1] + noise[i]
    return out


def _bump(hour: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * ((hour - centre) / width) ** 2)


# ---------------------------------------------------------------------------
# City-wide drivers
# ---------------------------------------------------------------------------


def _calendar(index: pd.DatetimeIndex) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hour": index.hour.to_numpy(),
            "weekend": (index.dayofweek >= 5).astype(float),
            "doy": (index.dayofyear - 1).to_numpy(),
        },
        index=index,
    )


def _city_weather(rng: np.random.Generator, cal: pd.DataFrame) -> pd.DataFrame:
    n = len(cal)
    hour = cal["hour"].to_numpy()
    seasonal = 3.5 + 0.085 * np.arange(n) / 24.0  # late winter into spring
    temperature = seasonal + 4.2 * np.sin(2 * np.pi * (hour - 9) / 24) + _ar1(rng, n, 0.985, 0.55)

    raining = np.zeros(n, dtype=bool)
    for i in range(1, n):
        raining[i] = rng.random() < (0.86 if raining[i - 1] else 0.018)
    precip = np.where(raining, rng.exponential(1.1, n), 0.0)

    humidity = 68 - 1.8 * (temperature - seasonal) + 14 * raining + _ar1(rng, n, 0.97, 1.4)
    wind = np.clip(4.2 + _ar1(rng, n, 0.96, 0.55) + 0.8 * np.sin(2 * np.pi * (hour - 14) / 24), 0.2, None)
    return pd.DataFrame(
        {"temperature": temperature, "humidity": np.clip(humidity, 25, 100), "wind": wind, "precip": precip},
        index=cal.index,
    )


# ---------------------------------------------------------------------------
# Per-zone generators
# ---------------------------------------------------------------------------


def _traffic_profile(hour: np.ndarray, weekend: np.ndarray) -> np.ndarray:
    weekday = 0.12 + 0.95 * _bump(hour, 8.0, 1.2) + 0.85 * _bump(hour, 17.5, 1.7) + 0.38 * _bump(hour, 12.5, 3.0)
    weekend_curve = 0.10 + 0.55 * _bump(hour, 13.0, 3.2) + 0.25 * _bump(hour, 20.0, 2.0)
    return np.where(weekend > 0, weekend_curve, weekday)


def _energy_profile(kind: str, hour: np.ndarray, weekend: np.ndarray) -> np.ndarray:
    wk = weekend > 0
    if kind == "residential":
        weekday = 0.62 + 0.30 * _bump(hour, 7.2, 1.3) + 0.62 * _bump(hour, 19.8, 2.2)
        weekend_curve = 0.66 + 0.22 * _bump(hour, 10.5, 2.6) + 0.58 * _bump(hour, 20.0, 2.5)
    elif kind == "commercial":
        weekday = 0.52 + 0.62 * _bump(hour, 13.0, 3.8)
        weekend_curve = 0.50 + 0.22 * _bump(hour, 14.0, 3.5)
    elif kind == "industrial":
        weekday = 0.70 + 0.34 * np.clip((hour - 5) / 2, 0, 1) * np.clip((22 - hour) / 2, 0, 1)
        weekend_curve = 0.62 + 0.10 * _bump(hour, 12.0, 4.0)
    elif kind == "harbor":
        weekday = 0.80 + 0.22 * _bump(hour, 10.0, 3.0) + 0.18 * _bump(hour, 21.0, 2.0)
        weekend_curve = 0.74 + 0.16 * _bump(hour, 11.0, 3.5)
    else:  # campus
        weekday = 0.45 + 0.72 * _bump(hour, 12.5, 3.4)
        weekend_curve = 0.36 + 0.12 * _bump(hour, 14.0, 3.0)
    return np.where(wk, weekend_curve, weekday)


def _zone_frames(rng: np.random.Generator, zone: str, cal: pd.DataFrame, city: pd.DataFrame) -> dict:
    p = PROFILES[zone]
    n = len(cal)
    hour = cal["hour"].to_numpy()
    weekend = cal["weekend"].to_numpy()
    rain = (city["precip"].to_numpy() > 0.05).astype(float)

    temperature = city["temperature"].to_numpy() + p.temp_offset + rng.normal(0, 0.25, n)
    wind = np.clip(city["wind"].to_numpy() + p.wind_offset + rng.normal(0, 0.3, n), 0.1, None)
    humidity = np.clip(city["humidity"].to_numpy() + rng.normal(0, 1.2, n), 20, 100)
    weather = pd.DataFrame(
        {
            "temperature_c": temperature,
            "humidity_pct": humidity,
            "wind_speed_ms": wind,
            "precipitation_mm": city["precip"].to_numpy() * rng.uniform(0.85, 1.15, n),
        },
        index=cal.index,
    )

    # Traffic: commuting profile, rain suppression, occasional events and incidents.
    demand = p.traffic_cap * p.traffic_scale * _traffic_profile(hour, weekend)
    demand *= 1 - 0.14 * rain
    demand *= np.exp(rng.normal(0, 0.07, n))
    event = np.zeros(n)
    for start in rng.choice(n - 6, size=7, replace=False):
        event[start : start + rng.integers(2, 5)] = rng.uniform(0.25, 0.5)
    if p.kind in ("commercial", "campus"):
        demand *= 1 + event
    count = np.round(p.traffic_cap * np.tanh(demand / p.traffic_cap))
    load_ratio = np.clip(count / p.traffic_cap, 0, 1.2)
    speed = np.clip(58 - 34 * load_ratio**1.6 - 3.5 * rain + rng.normal(0, 1.6, n), 6, 70)
    traffic = pd.DataFrame({"traffic_count": count, "avg_speed_kmh": speed}, index=cal.index)

    # Air quality: traffic and industrial sources, dispersed by wind, washed out by rain.
    industrial_shift = (p.kind == "industrial") * (weekend < 1) * _bump(hour, 13.0, 5.0)
    drive = (
        7.0
        + 0.0042 * count * p.emission_factor
        + 9.0 * industrial_shift
        + 2.2 * p.emission_factor
        - 0.95 * np.minimum(wind, 9)
        - 3.4 * rain
        + 2.6 * _bump(hour, 5.0, 3.0)  # nocturnal stagnation
    )
    pm25 = np.empty(n)
    pm25[0] = drive[0]
    shocks = _ar1(rng, n, 0.93, 0.9)
    for i in range(1, n):
        pm25[i] = 0.72 * pm25[i - 1] + 0.28 * drive[i] + shocks[i] * 0.35
    pm25 = np.clip(pm25, 1.0, None)
    occupancy = 55 * (p.kind in ("commercial", "campus")) * _bump(hour, 13.0, 3.5) * (1 - 0.6 * weekend)
    air = pd.DataFrame(
        {
            "pm25_ugm3": pm25,
            "pm10_ugm3": pm25 * rng.uniform(1.5, 1.9, n) + 3,
            "co2_ppm": 412 + 0.11 * count * p.emission_factor + occupancy + rng.normal(0, 7, n),
            "no2_ppb": np.clip(
                6
                + 0.011 * count * p.emission_factor
                + 4 * industrial_shift
                - 0.7 * np.minimum(wind, 9)
                + rng.normal(0, 1.4, n),
                0.5,
                None,
            ),
        },
        index=cal.index,
    )

    # Energy: occupancy profile scaled by heating demand and slow load drift.
    heating = 1 + 0.021 * np.clip(14.0 - temperature, 0, None) * (0.9 if p.kind == "residential" else 0.5)
    drift = np.exp(_ar1(rng, n, 0.96, 0.012))
    power_kw = p.base_kw * _energy_profile(p.kind, hour, weekend) * heating * drift
    power_kw *= 1 + 0.015 * rain
    power_kw = power_kw * np.exp(rng.normal(0, 0.012, n))
    return {"weather": weather, "traffic": traffic, "air_quality": air, "power_kw": power_kw, "profile": p}


# ---------------------------------------------------------------------------
# Energy telemetry and labelled anomalies
# ---------------------------------------------------------------------------


def _inject_energy_anomalies(rng, power_kw, voltage, reported_scale, zone_idx) -> np.ndarray:
    """Mutate the true load / telemetry in place and return a per-hour type label array."""
    n = len(power_kw)
    labels = np.full(n, "", dtype=object)
    plan = [("spike", 9), ("outage", 4), ("meter_fault", 4), ("voltage_sag", 6)]
    for kind, count in plan:
        for _ in range(count):
            start = int(rng.integers(24 * 8, n - 30))
            if labels[start : start + 26].any():
                continue
            if kind == "spike":
                length = int(rng.integers(1, 4))
                power_kw[start : start + length] *= rng.uniform(1.28, 2.1)
            elif kind == "outage":
                length = int(rng.integers(2, 8))
                power_kw[start : start + length] *= rng.uniform(0.0, 0.3)
            elif kind == "meter_fault":
                length = int(rng.integers(6, 20))
                factor = rng.choice([rng.uniform(1.15, 1.6), rng.uniform(0.55, 0.85)])
                reported_scale[start : start + length] = factor
            else:
                length = int(rng.integers(1, 4))
                voltage[start : start + length] *= rng.uniform(0.78, 0.9)
            labels[start : start + length] = kind
    return labels


def _energy_frame(rng, zone: str, cal, power_kw, zone_idx) -> tuple[pd.DataFrame, np.ndarray]:
    p = PROFILES[zone]
    n = len(cal)
    load_ratio = power_kw / p.base_kw
    voltage = NOMINAL_VOLTAGE * (1 + rng.normal(0, 0.006, n) - 0.006 * np.clip(load_ratio - 1, 0, None))
    reported_scale = np.ones(n)
    labels = _inject_energy_anomalies(rng, power_kw, voltage, reported_scale, zone_idx)

    hour = cal["hour"].to_numpy()
    pf_base = 0.90 if p.kind == "industrial" else 0.95
    power_factor = np.clip(pf_base + 0.02 * _bump(hour, 3, 4) + rng.normal(0, 0.012, n), 0.78, 0.995)

    # Feeder current follows physical three-phase power; sag events draw extra current.
    sag = np.clip(NOMINAL_VOLTAGE / voltage, 1.0, None)
    current = power_kw * 1000 / (np.sqrt(3) * voltage * power_factor) * np.where(labels == "voltage_sag", sag, 1.0)
    current *= np.exp(rng.normal(0, 0.022, n))
    energy = power_kw * reported_scale * np.exp(rng.normal(0, 0.018, n))
    frame = pd.DataFrame(
        {
            "energy_kwh": energy,
            "voltage_v": voltage,
            "current_a": current,
            "power_factor": power_factor,
        },
        index=cal.index,
    )
    return frame, labels


# ---------------------------------------------------------------------------
# Sensor reliability
# ---------------------------------------------------------------------------


def _degrade(rng, frame: pd.DataFrame, protected: np.ndarray | None = None) -> pd.DataFrame:
    """Add missing readings, noisy 'DEGRADED' stretches and OFFLINE gaps."""
    n = len(frame)
    status = np.full(n, "OK", dtype=object)
    values = frame.to_numpy(dtype=float, copy=True)
    keep = np.zeros(n, dtype=bool) if protected is None else protected

    for _ in range(max(2, n // 700)):
        start = int(rng.integers(0, n - 14))
        length = int(rng.integers(2, 13))
        block = slice(start, start + length)
        if keep[block].any():
            continue
        values[block] = np.nan
        status[block] = "OFFLINE"
    for _ in range(max(2, n // 500)):
        start = int(rng.integers(0, n - 10))
        length = int(rng.integers(2, 9))
        block = slice(start, start + length)
        if keep[block].any() or (status[block] == "OFFLINE").any():
            continue
        values[block] *= 1 + rng.normal(0, 0.06, (length, values.shape[1]))
        status[block] = "DEGRADED"
    scatter = (rng.random(values.shape) < 0.006) & ~keep[:, None]
    values[scatter] = np.nan

    out = pd.DataFrame(values, index=frame.index, columns=frame.columns)
    out["status"] = status
    return out


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def simulate(days: int = 120, seed: int = 2026, start: str = "2026-01-01") -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    index = pd.date_range(start, periods=days * 24, freq="h", name="timestamp")
    cal = _calendar(index)
    city = _city_weather(rng, cal)

    tables: dict[str, list[pd.DataFrame]] = {d: [] for d in ("weather", "traffic", "air_quality", "energy")}
    label_rows: list[pd.DataFrame] = []
    prefix = {"weather": "WX", "traffic": "TR", "air_quality": "AQ", "energy": "EN"}

    for zone_idx, zone in enumerate(ZONES):
        parts = _zone_frames(rng, zone, cal, city)
        energy, labels = _energy_frame(rng, zone, cal, parts["power_kw"], zone_idx)
        protected = labels != ""
        frames = {
            "weather": parts["weather"],
            "traffic": parts["traffic"],
            "air_quality": parts["air_quality"],
            "energy": energy,
        }
        for domain, frame in frames.items():
            frame = _degrade(rng, frame, protected if domain == "energy" else None)
            frame.insert(0, "device_id", f"{prefix[domain]}-{PROFILES[zone].code}-01")
            frame.insert(0, "zone", zone)
            tables[domain].append(frame.reset_index())
        hit = labels != ""
        if hit.any():
            label_rows.append(pd.DataFrame({"timestamp": index[hit], "zone": zone, "anomaly_type": labels[hit]}))

    result = {
        domain: pd.concat(parts, ignore_index=True).sort_values(["timestamp", "zone"]).reset_index(drop=True)
        for domain, parts in tables.items()
    }
    limits = {"humidity_pct": (0, 100), "power_factor": (0, 1), "traffic_count": (0, None), "avg_speed_kmh": (0, None)}
    for frame in result.values():
        for column, (low, high) in limits.items():
            if column in frame:
                frame[column] = frame[column].clip(low, high)
        numeric = frame.select_dtypes("number").columns
        frame[numeric] = frame[numeric].round(3)
    result["energy_anomaly_labels"] = (
        pd.concat(label_rows, ignore_index=True).sort_values(["timestamp", "zone"]).reset_index(drop=True)
    )
    return result


def write_dataset(settings: Settings, days: int = 120, seed: int = 2026) -> dict[str, int]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    tables = simulate(days=days, seed=seed)
    sizes = {}
    for name, frame in tables.items():
        frame.to_csv(settings.data_dir / f"{name}.csv", index=False, date_format="%Y-%m-%d %H:%M:%S")
        sizes[name] = len(frame)
    return sizes
