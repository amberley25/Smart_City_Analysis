"""Feature construction shared by training, evaluation and the serving API."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .config import ZONES

TEST_DAYS = 28
MAX_FILL_HOURS = 6
HORIZONS = (1, 24)

CALENDAR = ["hour_sin", "hour_cos", "dow", "is_weekend"]
WEATHER = ["temperature_c", "humidity_pct", "wind_speed_ms", "precipitation_mm"]
ZONE_COLUMNS = [f"zone_{z}" for z in ZONES]


def forecast_feature_names() -> list[str]:
    return [
        "energy_now",
        "energy_lag_1",
        "energy_lag_2",
        "energy_lag_3",
        "energy_lag_6",
        "same_hour_yesterday",
        "same_hour_last_week",
        "mean_24h",
        "std_24h",
        "traffic_now",
        "traffic_mean_24h",
        "temp_now",
        *[f"target_{c}" for c in WEATHER],
        *[f"target_{c}" for c in CALENDAR],
        *ZONE_COLUMNS,
    ]


def build_panel(energy: pd.DataFrame, weather: pd.DataFrame, traffic: pd.DataFrame) -> pd.DataFrame:
    """Join the three sources on a complete (zone x hour) grid."""
    index = pd.date_range(energy["timestamp"].min(), energy["timestamp"].max(), freq="h")
    grid = pd.MultiIndex.from_product([ZONES, index], names=["zone", "timestamp"]).to_frame(index=False)
    panel = grid.merge(energy[["zone", "timestamp", "energy_kwh"]], how="left", on=["zone", "timestamp"])
    panel = panel.merge(weather[["zone", "timestamp", *WEATHER]], how="left", on=["zone", "timestamp"]).merge(
        traffic[["zone", "timestamp", "traffic_count"]], how="left", on=["zone", "timestamp"]
    )
    return panel.sort_values(["zone", "timestamp"]).reset_index(drop=True)


def _calendar(ts: pd.Series) -> pd.DataFrame:
    hour = ts.dt.hour.to_numpy()
    return pd.DataFrame(
        {
            "hour_sin": np.sin(2 * np.pi * hour / 24),
            "hour_cos": np.cos(2 * np.pi * hour / 24),
            "dow": ts.dt.dayofweek.to_numpy(),
            "is_weekend": (ts.dt.dayofweek >= 5).astype(int).to_numpy(),
        }
    )


def make_forecast_frame(panel: pd.DataFrame, horizon: int, with_target: bool = True) -> pd.DataFrame:
    """One row per (zone, origin hour) predicting energy `horizon` hours ahead.

    Everything is observable at the origin, except weather at the target hour, which stands in
    for a numerical weather forecast (documented in docs/MODEL_CARD.md).
    """
    frames = []
    for zone, g in panel.groupby("zone", sort=False):
        g = g.sort_values("timestamp").reset_index(drop=True)
        energy = g["energy_kwh"].ffill(limit=MAX_FILL_HOURS)
        traffic = g["traffic_count"].ffill(limit=MAX_FILL_HOURS)
        target_ts = g["timestamp"] + pd.Timedelta(hours=horizon)

        out = pd.DataFrame({"zone": zone, "origin": g["timestamp"], "target_time": target_ts})
        out["energy_now"] = energy
        for k in (1, 2, 3, 6):
            out[f"energy_lag_{k}"] = energy.shift(k)
        out["same_hour_yesterday"] = energy.shift(24 - horizon) if horizon <= 24 else np.nan
        out["same_hour_last_week"] = energy.shift(168 - horizon)
        out["mean_24h"] = energy.rolling(24, min_periods=12).mean()
        out["std_24h"] = energy.rolling(24, min_periods=12).std()
        out["traffic_now"] = traffic
        out["traffic_mean_24h"] = traffic.rolling(24, min_periods=12).mean()
        out["temp_now"] = g["temperature_c"].ffill(limit=MAX_FILL_HOURS)
        for column in WEATHER:
            out[f"target_{column}"] = g[column].ffill(limit=MAX_FILL_HOURS).shift(-horizon)
        cal = _calendar(target_ts)
        for column in CALENDAR:
            out[f"target_{column}"] = cal[column].to_numpy()
        for z in ZONES:
            out[f"zone_{z}"] = int(zone == z)
        if with_target:
            out["target"] = g["energy_kwh"].shift(-horizon)
        frames.append(out)

    frame = pd.concat(frames, ignore_index=True).sort_values(["origin", "zone"]).reset_index(drop=True)
    return frame


def split_by_time(frame: pd.DataFrame, horizon: int, test_days: int = TEST_DAYS):
    """Chronological split. Training targets never overlap the test window."""
    cutoff = frame["origin"].max() - pd.Timedelta(days=test_days)
    # The first week has no weekly lag; those warm-up rows are not usable examples.
    usable = frame["target"].notna() & frame["same_hour_last_week"].notna()
    train = frame[(frame["target_time"] <= cutoff) & usable]
    test = frame[(frame["origin"] > cutoff) & usable]
    return train.reset_index(drop=True), test.reset_index(drop=True), cutoff
