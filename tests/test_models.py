import numpy as np
import pandas as pd

from smartcity import anomaly, forecasting


def test_persistence_baseline_prefers_column_then_fallback():
    X = pd.DataFrame({"energy_now": [10.0, np.nan, np.nan], "mean_24h": [1.0, 2.0, np.nan]})
    model = forecasting.PersistenceBaseline("energy_now").fit(X, pd.Series([4.0, 6.0, 8.0]))
    assert list(model.predict(X)) == [10.0, 2.0, 6.0]


def test_smape_is_symmetric_and_bounded():
    a, b = np.array([100.0, 200.0]), np.array([110.0, 180.0])
    assert forecasting.smape(a, b) == forecasting.smape(b, a)
    assert 0 <= forecasting.smape(a, np.zeros(2)) <= 200


def test_regression_metrics_perfect_forecast():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    m = forecasting.regression_metrics(y, y)
    assert m["mae"] == 0 and m["rmse"] == 0 and m["r2"] == 1


def test_forecast_beats_naive_baselines(metrics):
    for block in metrics["forecast"].values():
        rows = {r["name"]: r for r in block["models"]}
        best = rows[block["best_model"]]
        assert best["test_mae"] < min(rows["Persistence"]["test_mae"], rows["Seasonal naive (24h)"]["test_mae"])
        assert best["test_r2"] > 0.85
        assert block["improvement_vs_best_baseline_pct"] > 0


def test_prediction_interval_coverage_is_close_to_nominal(metrics):
    for block in metrics["forecast"].values():
        assert 0.8 <= block["interval"]["empirical"] <= 0.99


def test_holdout_is_chronological_and_after_training(metrics):
    block = metrics["forecast"]["1"]
    assert block["test_start"] > metrics["dataset"]["holdout_start"]


def test_anomaly_detector_ranks_faults_above_normal_readings(metrics):
    methods = {m["name"]: m for m in metrics["anomaly"]["methods"]}
    engineered = methods["Isolation forest (engineered features)"]
    assert engineered["roc_auc"] > 0.95
    assert engineered["roc_auc"] > methods["Isolation forest (raw readings)"]["roc_auc"]
    assert engineered["precision"] > 0.5


def test_explanations_name_the_problem():
    base = {"log_ratio": 0.0, "power_balance": 0.0, "voltage_dev": 0.0, "power_factor": 0.95}
    assert "2.0x" in anomaly.explain({**base, "log_ratio": np.log(2.0)})[0]
    assert "below the typical" in anomaly.explain({**base, "log_ratio": np.log(0.2)})[0]
    assert "meter" in anomaly.explain({**base, "power_balance": 0.4})[0]
    assert "below nominal" in anomaly.explain({**base, "voltage_dev": -0.15})[0]
    assert anomaly.explain(base)


def test_profile_stats_use_robust_statistics():
    ts = pd.date_range("2026-01-05", periods=24 * 14, freq="h")
    frame = pd.DataFrame({"timestamp": ts, "zone": "Downtown", "energy_kwh": 100.0})
    frame.loc[5, "energy_kwh"] = 10_000.0  # a single huge outlier must not move the profile
    stats = anomaly.ProfileStats.fit(frame)
    median, spread = stats.lookup(frame.iloc[[5]])
    assert median[0] == 100.0 and spread[0] > 0
