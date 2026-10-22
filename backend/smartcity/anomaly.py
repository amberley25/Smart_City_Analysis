"""Unsupervised detection of abnormal substation telemetry.

The detector never sees labels. Features describe how far a reading sits from the zone's own
typical profile and whether the electrical measurements agree with the metered energy.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score, roc_curve
from sklearn.pipeline import Pipeline

from .simulate import NOMINAL_VOLTAGE

ALERT_RATE = 0.025  # fraction of training readings the operator is willing to review
VOLTAGE_LIMIT = 0.10  # low-voltage grid tolerance (+/-10% of nominal); a hard rule, not a learned one
RULE_BONUS = 1.0  # lifts rule violations above any learned score
FEATURES = ["profile_z", "log_ratio", "power_balance", "voltage_dev", "power_factor"]
RAW_FEATURES = ["energy_kwh", "power_factor", "voltage_v", "current_a"]
SEED = 42
SQRT3 = float(np.sqrt(3))


class ProfileStats:
    """Robust (median / MAD) energy profile per zone, hour of day and weekday type."""

    def __init__(self, table: pd.DataFrame, floor: dict[str, float]):
        self.table = table
        self.floor = floor

    @classmethod
    def fit(cls, frame: pd.DataFrame) -> ProfileStats:
        keyed = cls._keys(frame).dropna(subset=["energy_kwh"])
        grouped = keyed.groupby(["zone", "hour", "weekend"])["energy_kwh"]
        median = grouped.median()
        mad = grouped.apply(lambda s: np.median(np.abs(s - np.median(s))) * 1.4826)
        table = pd.DataFrame({"median": median, "mad": mad})
        floor = (keyed.groupby("zone")["energy_kwh"].median() * 0.03).to_dict()
        return cls(table, floor)

    @staticmethod
    def _keys(frame: pd.DataFrame) -> pd.DataFrame:
        out = frame.copy()
        ts = pd.to_datetime(out["timestamp"])
        out["hour"] = ts.dt.hour
        out["weekend"] = (ts.dt.dayofweek >= 5).astype(int)
        return out

    def lookup(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        keyed = self._keys(frame)
        joined = keyed.join(self.table, on=["zone", "hour", "weekend"])
        median = joined["median"].to_numpy(dtype=float)
        mad = joined["mad"].to_numpy(dtype=float)
        floor = keyed["zone"].map(self.floor).to_numpy(dtype=float)
        return median, np.maximum(mad, floor)

    def to_dict(self) -> dict:
        return {
            "table": {f"{z}|{h}|{w}": [float(r["median"]), float(r["mad"])] for (z, h, w), r in self.table.iterrows()},
            "floor": self.floor,
        }


def engineer(frame: pd.DataFrame, stats: ProfileStats) -> pd.DataFrame:
    median, spread = stats.lookup(frame)
    energy = frame["energy_kwh"].to_numpy(dtype=float)
    voltage = frame["voltage_v"].to_numpy(dtype=float)
    current = frame["current_a"].to_numpy(dtype=float)
    pf = frame["power_factor"].to_numpy(dtype=float)
    electrical_kw = SQRT3 * voltage * current * pf / 1000.0
    out = pd.DataFrame(
        {
            "profile_z": np.clip((energy - median) / spread, -40, 40),
            "log_ratio": np.log((energy + 5.0) / (median + 5.0)),
            "power_balance": np.clip((electrical_kw - energy) / (energy + 5.0), -3, 3),
            "voltage_dev": voltage / NOMINAL_VOLTAGE - 1.0,
            "power_factor": pf,
        },
        index=frame.index,
    )
    return out


def build_detector() -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("forest", IsolationForest(n_estimators=300, contamination="auto", random_state=SEED, n_jobs=-1)),
        ]
    )


def forest_score(detector: Pipeline, X: pd.DataFrame) -> np.ndarray:
    """Isolation-forest anomaly score; higher means more anomalous."""
    return -detector.named_steps["forest"].score_samples(detector.named_steps["impute"].transform(X))


def anomaly_score(detector: Pipeline, features: pd.DataFrame) -> np.ndarray:
    """Learned score plus a deterministic voltage-limit rule.

    Isolation forests are weak on a single rarely-varying feature, and a voltage excursion beyond
    grid tolerance is something an operator must always see, so it is enforced explicitly.
    """
    score = forest_score(detector, features[FEATURES])
    violation = np.abs(features["voltage_dev"].to_numpy(dtype=float)) > VOLTAGE_LIMIT
    return score + RULE_BONUS * np.nan_to_num(violation.astype(float))


def explain(row: dict) -> list[str]:
    """Plain-language reasons derived from the engineered features."""
    reasons = []
    ratio = float(np.exp(row["log_ratio"]))
    if ratio > 1.45:
        reasons.append(f"Demand is {ratio:.1f}x the typical level for this hour")
    elif ratio < 0.55:
        reasons.append(f"Demand is {100 * (1 - ratio):.0f}% below the typical level for this hour")
    if abs(row["power_balance"]) > 0.25:
        reasons.append(
            f"Metered energy disagrees with V x I x pf by {abs(row['power_balance']) * 100:.0f}% (possible meter fault)"
        )
    if abs(row["voltage_dev"]) > 0.06:
        reasons.append(
            f"Voltage is {abs(row['voltage_dev']) * 100:.0f}% {'below' if row['voltage_dev'] < 0 else 'above'} nominal"
        )
    if row["power_factor"] < 0.82:
        reasons.append(f"Power factor is low ({row['power_factor']:.2f})")
    return reasons or ["Combination of readings is unusual for this zone and hour"]


def _curve_points(x, y, limit: int = 60) -> list[list[float]]:
    x, y = np.asarray(x), np.asarray(y)
    if len(x) > limit:
        pick = np.unique(np.linspace(0, len(x) - 1, limit).astype(int))
        x, y = x[pick], y[pick]
    return [[round(float(a), 4), round(float(b), 4)] for a, b in zip(x, y, strict=True)]


def evaluate(train: pd.DataFrame, test: pd.DataFrame, test_truth: pd.Series, test_type: pd.Series) -> dict:
    """Fit detectors on `train` and score them on labelled `test`.

    Three methods share one alert budget: the threshold is the (1 - ALERT_RATE) quantile of the
    training scores, so no method is favoured by tuning on the test labels.
    """
    stats = ProfileStats.fit(train)
    f_train, f_test = engineer(train, stats), engineer(test, stats)

    forest = build_detector().fit(f_train[FEATURES])
    raw = build_detector().fit(train[RAW_FEATURES])

    methods = {
        "Isolation forest (engineered features)": (
            anomaly_score(forest, f_train),
            anomaly_score(forest, f_test),
        ),
        "Isolation forest (raw readings)": (
            forest_score(raw, train[RAW_FEATURES]),
            forest_score(raw, test[RAW_FEATURES]),
        ),
        "Robust z-score (energy only)": (
            np.abs(f_train["profile_z"].fillna(0).to_numpy()),
            np.abs(f_test["profile_z"].fillna(0).to_numpy()),
        ),
    }

    y = test_truth.to_numpy().astype(int)
    results, curves, primary = [], {}, None
    for name, (train_score, test_score) in methods.items():
        threshold = float(np.quantile(train_score, 1 - ALERT_RATE))
        flagged = test_score >= threshold
        tp = int((flagged & (y == 1)).sum())
        fp = int((flagged & (y == 0)).sum())
        fn = int((~flagged & (y == 1)).sum())
        tn = int((~flagged & (y == 0)).sum())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        fpr, tpr, _ = roc_curve(y, test_score)
        prec, rec, _ = precision_recall_curve(y, test_score)
        results.append(
            {
                "name": name,
                "roc_auc": float(roc_auc_score(y, test_score)),
                "pr_auc": float(average_precision_score(y, test_score)),
                "precision": precision,
                "recall": recall,
                "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
                "threshold": threshold,
                "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
            }
        )
        curves[name] = {"roc": _curve_points(fpr, tpr), "pr": _curve_points(rec, prec)}
        if primary is None:
            primary = (flagged, test_score, threshold)

    flagged = primary[0]
    per_type = []
    for kind in ["spike", "outage", "meter_fault", "voltage_sag"]:
        mask = (test_type == kind).to_numpy()
        per_type.append(
            {"type": kind, "count": int(mask.sum()), "recall": float(flagged[mask].mean()) if mask.any() else None}
        )

    return {
        "results": results,
        "curves": curves,
        "per_type": per_type,
        "alert_rate": ALERT_RATE,
        "n_test": int(len(y)),
        "n_positive": int(y.sum()),
        "bundle": {
            "stats": stats,
            "detector": forest,
            "threshold": results[0]["threshold"],
        },
        "test_scores": primary[1],
        "test_flagged": primary[0],
    }


def dump_json(path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2))
