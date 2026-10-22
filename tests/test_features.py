import numpy as np
import pandas as pd
import pytest

from smartcity import features


@pytest.fixture(scope="module")
def panel(tables):
    return features.build_panel(tables["energy"], tables["weather"], tables["traffic"])


@pytest.mark.parametrize("horizon", features.HORIZONS)
def test_frame_has_expected_shape(panel, horizon):
    frame = features.make_forecast_frame(panel, horizon)
    for name in features.forecast_feature_names():
        assert name in frame.columns
    assert (frame["target_time"] - frame["origin"] == pd.Timedelta(hours=horizon)).all()
    assert frame[features.ZONE_COLUMNS].sum(axis=1).eq(1).all()


@pytest.mark.parametrize("horizon", features.HORIZONS)
def test_features_never_use_information_after_the_origin(panel, horizon):
    """Corrupting every energy/traffic value after t must not change the features at t."""
    origin = panel["timestamp"].iloc[24 * 15]
    base = features.make_forecast_frame(panel, horizon)
    tampered = panel.copy()
    future = tampered["timestamp"] > origin
    tampered.loc[future, ["energy_kwh", "traffic_count"]] = 1e9
    other = features.make_forecast_frame(tampered, horizon)

    cols = [c for c in features.forecast_feature_names() if not c.startswith("target_")]
    a = base[base["origin"] == origin][cols].reset_index(drop=True)
    b = other[other["origin"] == origin][cols].reset_index(drop=True)
    pd.testing.assert_frame_equal(a, b)


def test_seasonal_references_line_up_with_the_target_hour(panel):
    frame = features.make_forecast_frame(panel, horizon=1)
    zone = frame[frame["zone"] == "Downtown"].reset_index(drop=True)
    series = (
        panel[panel["zone"] == "Downtown"].set_index("timestamp")["energy_kwh"].ffill(limit=features.MAX_FILL_HOURS)
    )
    row = zone.iloc[300]
    target = row["target_time"]
    assert row["same_hour_yesterday"] == series.get(target - pd.Timedelta(hours=24))
    assert row["same_hour_last_week"] == series.get(target - pd.Timedelta(hours=168))


def test_time_split_leaves_no_overlap(panel):
    frame = features.make_forecast_frame(panel, horizon=24)
    train, test, cutoff = features.split_by_time(frame, 24)
    assert train["target_time"].max() <= cutoff
    assert test["origin"].min() > cutoff
    assert train["target"].notna().all() and test["target"].notna().all()
    assert (test["origin"].max() - cutoff) <= pd.Timedelta(days=features.TEST_DAYS)


def test_calendar_encoding_is_cyclic():
    ts = pd.Series(pd.to_datetime(["2026-01-05 00:00", "2026-01-05 23:00", "2026-01-10 12:00"]))
    cal = features._calendar(ts)
    assert np.isclose(cal["hour_sin"].iloc[0], 0) and np.isclose(cal["hour_cos"].iloc[0], 1)
    assert abs(cal["hour_sin"].iloc[1]) < 0.3
    assert list(cal["is_weekend"]) == [0, 0, 1]
