from __future__ import annotations

import pytest

from smartcity import db, forecasting, pipeline, simulate
from smartcity.api import create_app
from smartcity.config import Settings
from smartcity.forecasting import PersistenceBaseline


def _light_models():
    """Same candidates as production, with smaller ensembles so the suite stays fast."""
    from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
    from sklearn.impute import SimpleImputer
    from sklearn.linear_model import Ridge
    from sklearn.pipeline import Pipeline
    from sklearn.preprocessing import StandardScaler

    return {
        "Persistence": PersistenceBaseline("energy_now"),
        "Seasonal naive (24h)": PersistenceBaseline("same_hour_yesterday"),
        "Ridge": Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler()), ("m", Ridge(alpha=3.0))]),
        "Random forest": Pipeline(
            [
                ("i", SimpleImputer(strategy="median")),
                (
                    "m",
                    RandomForestRegressor(n_estimators=40, max_depth=10, min_samples_leaf=4, n_jobs=-1, random_state=0),
                ),
            ]
        ),
        "Gradient boosting": HistGradientBoostingRegressor(max_iter=80, learning_rate=0.1, random_state=0),
    }


@pytest.fixture(scope="session")
def trained(tmp_path_factory):
    """A complete, isolated environment: simulated data, SQLite database and trained models."""
    root = tmp_path_factory.mktemp("smartcity")
    settings = Settings(
        home=root,
        data_dir=root / "dataset",
        db_path=root / "var" / "test.db",
        model_dir=root / "var" / "models",
        report_dir=root / "var" / "reports",
        figure_dir=root / "figures",
    )
    simulate.write_dataset(settings, days=60, seed=11)
    db.ingest_csvs(settings)

    original = forecasting.candidate_models
    forecasting.candidate_models = _light_models
    try:
        artifacts = pipeline.run(settings)
    finally:
        forecasting.candidate_models = original
    return settings, artifacts


@pytest.fixture(scope="session")
def settings(trained):
    return trained[0]


@pytest.fixture(scope="session")
def metrics(trained):
    return trained[1]["metrics"]


@pytest.fixture()
def client(settings):
    app = create_app(settings)
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture(scope="session")
def tables():
    return simulate.simulate(days=45, seed=5)
