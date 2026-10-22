import numpy as np
import pandas as pd

from smartcity import simulate
from smartcity.config import ZONES


def test_simulation_is_deterministic():
    a = simulate.simulate(days=10, seed=3)
    b = simulate.simulate(days=10, seed=3)
    for name in a:
        pd.testing.assert_frame_equal(a[name], b[name])


def test_different_seeds_differ():
    a = simulate.simulate(days=10, seed=3)["energy"]["energy_kwh"]
    b = simulate.simulate(days=10, seed=4)["energy"]["energy_kwh"]
    assert not a.equals(b)


def test_grid_is_complete_and_unique(tables):
    for domain in ("energy", "traffic", "air_quality", "weather"):
        frame = tables[domain]
        assert len(frame) == 45 * 24 * len(ZONES)
        assert not frame.duplicated(["zone", "timestamp"]).any()
        assert set(frame["zone"]) == set(ZONES)


def test_value_ranges(tables):
    assert tables["weather"]["humidity_pct"].dropna().between(0, 100).all()
    assert (tables["traffic"]["traffic_count"].dropna() >= 0).all()
    assert tables["energy"]["power_factor"].dropna().between(0.5, 1.0).all()
    assert (tables["air_quality"]["pm25_ugm3"].dropna() > 0).all()


def test_sensor_faults_are_present_but_rare(tables):
    energy = tables["energy"]
    assert set(energy["status"]) <= {"OK", "DEGRADED", "OFFLINE"}
    assert 0 < energy["status"].ne("OK").mean() < 0.1
    offline = energy[energy["status"] == "OFFLINE"]
    assert offline[["energy_kwh", "voltage_v"]].isna().all().all()


def test_electrical_readings_agree_with_metered_energy_when_healthy(tables):
    energy = tables["energy"]
    labelled = tables["energy_anomaly_labels"]
    clean = energy.merge(labelled, how="left", on=["zone", "timestamp"])
    clean = clean[clean["anomaly_type"].isna() & (clean["status"] == "OK")].drop(columns="anomaly_type").dropna()
    electrical = np.sqrt(3) * clean["voltage_v"] * clean["current_a"] * clean["power_factor"] / 1000
    ratio = electrical / clean["energy_kwh"]
    assert abs(ratio.median() - 1) < 0.02
    assert ratio.quantile(0.99) < 1.15


def test_labels_point_at_real_rows(tables):
    labels, energy = tables["energy_anomaly_labels"], tables["energy"]
    joined = labels.merge(energy, on=["zone", "timestamp"], how="left", indicator=True)
    assert (joined["_merge"] == "both").all()
    assert set(labels["anomaly_type"]) <= {"spike", "outage", "meter_fault", "voltage_sag"}
    # anomalous rows are protected from being blanked out by sensor outages
    assert joined["energy_kwh"].notna().all()


def test_heating_demand_rises_when_it_is_cold(tables):
    res = tables["energy"][tables["energy"]["zone"] == "Residential"].merge(
        tables["weather"][tables["weather"]["zone"] == "Residential"][["timestamp", "temperature_c"]], on="timestamp"
    )
    res = res.assign(day=res["timestamp"].dt.floor("D")).groupby("day")[["energy_kwh", "temperature_c"]].mean()
    assert res.corr().iloc[0, 1] < -0.2


def test_traffic_drives_particulates(tables):
    merged = (
        tables["traffic"][["zone", "timestamp", "traffic_count"]]
        .merge(tables["air_quality"][["zone", "timestamp", "pm25_ugm3"]], on=["zone", "timestamp"])
        .dropna()
    )
    sub = merged[merged["zone"] == "Downtown"]
    assert sub["traffic_count"].corr(sub["pm25_ugm3"]) > 0.3
