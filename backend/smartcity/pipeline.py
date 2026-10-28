"""End-to-end training: forecasting, anomaly detection, persistence and metrics export."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd

from . import anomaly, db, forecasting
from .config import ZONES, Settings
from .features import HORIZONS, TEST_DAYS, build_panel, forecast_feature_names, make_forecast_frame, split_by_time

log = logging.getLogger(__name__)


def _load_labels(settings: Settings) -> pd.DataFrame:
    labels = pd.read_csv(settings.labels_path, parse_dates=["timestamp"])
    return labels


def _round(value, digits=4):
    return None if value is None else round(float(value), digits)


def train_forecasters(settings: Settings, energy, weather, traffic, labels) -> tuple[dict, dict]:
    panel = build_panel(energy, weather, traffic)
    flagged = labels.assign(is_anomaly=True)[["zone", "timestamp", "is_anomaly"]]
    summary, artifacts = {}, {}

    for horizon in HORIZONS:
        frame = make_forecast_frame(panel, horizon)
        train, test, cutoff = split_by_time(frame, horizon)
        test_keys = test[["zone", "target_time"]].rename(columns={"target_time": "timestamp"})
        is_bad = (
            test_keys.merge(flagged, how="left", on=["zone", "timestamp"])["is_anomaly"].fillna(False).to_numpy(bool)
        )
        result = forecasting.train_and_evaluate(train, test, ~is_bad)

        joblib.dump(
            {
                "model": result["model"],
                "name": result["best"],
                "horizon": horizon,
                "features": forecast_feature_names(),
                "halfwidth": result["halfwidth"],
                "coverage": forecasting.INTERVAL_COVERAGE,
                "trained_through": str(train["target_time"].max()),
            },
            settings.model_dir / f"forecast_h{horizon}.joblib",
        )

        pred = result["pred"]
        width = test["zone"].map(result["halfwidth"]).to_numpy()
        residual = test["target"].to_numpy() - pred
        hist, edges = np.histogram(residual, bins=40, range=tuple(np.quantile(residual, [0.005, 0.995])))
        by_hour = (
            pd.DataFrame({"hour": test["target_time"].dt.hour, "abs_err": np.abs(residual)})
            .groupby("hour")["abs_err"]
            .mean()
        )
        window_start = test["target_time"].max() - pd.Timedelta(days=7)
        in_window = (test["target_time"] > window_start).to_numpy()
        backtest = pd.DataFrame(
            {
                "timestamp": test["target_time"][in_window].dt.strftime("%Y-%m-%dT%H:%M:%S"),
                "zone": test["zone"][in_window],
                "actual": test["target"][in_window].round(2),
                "predicted": np.round(pred[in_window], 2),
                "lower": np.round(pred[in_window] - width[in_window], 2),
                "upper": np.round(pred[in_window] + width[in_window], 2),
            }
        )
        sample = np.random.default_rng(7).choice(len(test), size=min(600, len(test)), replace=False)
        per_zone = {zone: _round(np.mean(np.abs(residual[(test["zone"] == zone).to_numpy()])), 2) for zone in ZONES}
        best_row = next(r for r in result["rows"] if r["name"] == result["best"])
        naive = next(r for r in result["rows"] if r["name"] == "Persistence")
        seasonal = next(r for r in result["rows"] if r["name"] == "Seasonal naive (24h)")
        reference = min(naive["test_mae"], seasonal["test_mae"])

        summary[str(horizon)] = {
            "horizon_hours": horizon,
            "best_model": result["best"],
            "train_rows": int(len(train)),
            "test_rows": int(len(test)),
            "test_start": str(test["origin"].min()),
            "test_end": str(test["target_time"].max()),
            "models": [
                {k: (_round(v) if isinstance(v, float) else v) for k, v in row.items()} for row in result["rows"]
            ],
            "improvement_vs_best_baseline_pct": _round(100 * (1 - best_row["test_mae"] / reference), 1),
            "interval": {"nominal": forecasting.INTERVAL_COVERAGE, "empirical": _round(result["coverage"])},
            "mae_by_zone": per_zone,
            "residual_histogram": {"counts": hist.tolist(), "edges": [round(float(e), 2) for e in edges]},
            "mae_by_hour": {int(h): _round(v, 2) for h, v in by_hour.items()},
            "feature_importance": [
                {"feature": f, "importance": _round(v, 3)} for f, v in result["importance"].head(12).items()
            ],
            "scatter": [[_round(test["target"].iloc[i], 1), _round(pred[i], 1)] for i in sorted(sample)],
            "backtest": backtest.to_dict("records"),
        }
        artifacts[horizon] = {"result": result, "test": test, "cutoff": cutoff, "residual": residual, "width": width}
        log.info("h=%s best=%s test MAE=%.2f", horizon, result["best"], best_row["test_mae"])
    return summary, artifacts


def train_anomaly_detector(settings: Settings, energy: pd.DataFrame, labels: pd.DataFrame):
    data = energy[energy["status"] != "OFFLINE"].dropna(subset=["energy_kwh", "voltage_v", "current_a", "power_factor"])
    data = data.merge(labels, how="left", on=["zone", "timestamp"])
    data["truth"] = data["anomaly_type"].notna()
    cutoff = energy["timestamp"].max() - pd.Timedelta(days=TEST_DAYS)
    train, test = data[data["timestamp"] <= cutoff], data[data["timestamp"] > cutoff]
    result = anomaly.evaluate(train, test, test["truth"], test["anomaly_type"])

    joblib.dump(result["bundle"], settings.model_dir / "anomaly_detector.joblib")
    return result, data, train, test, cutoff


def score_history(settings: Settings, bundle: dict, data: pd.DataFrame) -> int:
    features = anomaly.engineer(data, bundle["stats"])
    score = anomaly.anomaly_score(bundle["detector"], features)
    flagged = score >= bundle["threshold"]
    reasons = [
        json.dumps(anomaly.explain(features.iloc[i].to_dict())) if flagged[i] else None for i in range(len(features))
    ]
    out = pd.DataFrame(
        {
            "timestamp": data["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S"),
            "zone": data["zone"],
            "score": np.round(score, 4),
            "flagged": flagged.astype(int),
            "reasons": reasons,
            "true_type": data["anomaly_type"].where(data["anomaly_type"].notna(), None),
        }
    )
    with db.session(settings) as conn:
        conn.execute("DELETE FROM energy_anomalies")
        out.to_sql("energy_anomalies", conn, if_exists="append", index=False)
    return int(flagged.sum())


def run(settings: Settings) -> dict:
    settings.model_dir.mkdir(parents=True, exist_ok=True)
    settings.report_dir.mkdir(parents=True, exist_ok=True)
    db.init_schema(settings)

    energy, weather, traffic = (db.read_frame(settings, d) for d in ("energy", "weather", "traffic"))
    labels = _load_labels(settings)

    forecast_summary, forecast_artifacts = train_forecasters(settings, energy, weather, traffic, labels)
    anomaly_result, data, a_train, a_test, a_cutoff = train_anomaly_detector(settings, energy, labels)
    flagged_total = score_history(settings, anomaly_result["bundle"], data)

    metrics = {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "dataset": {
            "zones": ZONES,
            "start": str(energy["timestamp"].min()),
            "end": str(energy["timestamp"].max()),
            "energy_rows": int(len(energy)),
            "holdout_days": TEST_DAYS,
            "holdout_start": str(forecast_artifacts[HORIZONS[0]]["cutoff"]),
            "labelled_anomaly_hours": int(len(labels)),
        },
        "forecast": forecast_summary,
        "anomaly": {
            "methods": [
                {k: (_round(v) if isinstance(v, float) else v) for k, v in row.items()}
                for row in anomaly_result["results"]
            ],
            "curves": anomaly_result["curves"],
            "per_type": [
                {**r, "recall": _round(r["recall"]), "recall_without_rule": _round(r["recall_without_rule"])}
                for r in anomaly_result["per_type"]
            ],
            "alert_rate": anomaly_result["alert_rate"],
            "holdout_rows": anomaly_result["n_test"],
            "holdout_anomalies": anomaly_result["n_positive"],
            "flagged_total": flagged_total,
        },
    }
    anomaly.dump_json(settings.metrics_path, metrics)

    return {
        "metrics": metrics,
        "forecast": forecast_artifacts,
        "anomaly": anomaly_result,
        "anomaly_frames": {"data": data, "train": a_train, "test": a_test, "cutoff": a_cutoff},
        "energy": energy,
    }
