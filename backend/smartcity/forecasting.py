"""Energy demand forecasting: candidate models, time-series CV and holdout evaluation."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin, clone
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import forecast_feature_names

INTERVAL_COVERAGE = 0.90
SEED = 42


class PersistenceBaseline(BaseEstimator, RegressorMixin):
    """Predict a single feature column unchanged (naive / seasonal-naive benchmarks)."""

    def __init__(self, column: str = "energy_now", fallback: str = "mean_24h"):
        self.column = column
        self.fallback = fallback

    def fit(self, X, y=None):
        self.global_mean_ = float(np.nanmean(y)) if y is not None else 0.0
        return self

    def predict(self, X):
        values = X[self.column].to_numpy(dtype=float)
        backup = X[self.fallback].to_numpy(dtype=float)
        values = np.where(np.isnan(values), backup, values)
        return np.where(np.isnan(values), self.global_mean_, values)


def candidate_models() -> dict[str, BaseEstimator]:
    return {
        "Persistence": PersistenceBaseline("energy_now"),
        "Seasonal naive (24h)": PersistenceBaseline("same_hour_yesterday"),
        "Ridge": Pipeline(
            [("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler()), ("model", Ridge(alpha=3.0))]
        ),
        "Random forest": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=200, max_depth=14, min_samples_leaf=4, n_jobs=-1, random_state=SEED
                    ),
                ),
            ]
        ),
        "Gradient boosting": HistGradientBoostingRegressor(
            max_iter=350,
            learning_rate=0.06,
            max_leaf_nodes=24,
            min_samples_leaf=30,
            l2_regularization=1.0,
            random_state=SEED,
        ),
    }


def smape(y_true, y_pred) -> float:
    denom = (np.abs(y_true) + np.abs(y_pred)) / 2
    return float(np.mean(np.abs(y_true - y_pred) / np.maximum(denom, 1e-9)) * 100)


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
        "smape": smape(np.asarray(y_true), np.asarray(y_pred)),
    }


def _cv_scores(model, X: pd.DataFrame, y: pd.Series, n_splits: int = 5):
    maes, oof_idx, oof_pred = [], [], []
    for fit_idx, val_idx in TimeSeriesSplit(n_splits=n_splits).split(X):
        fitted = clone(model).fit(X.iloc[fit_idx], y.iloc[fit_idx])
        pred = fitted.predict(X.iloc[val_idx])
        maes.append(mean_absolute_error(y.iloc[val_idx], pred))
        oof_idx.append(val_idx)
        oof_pred.append(pred)
    return np.array(maes), np.concatenate(oof_idx), np.concatenate(oof_pred)


def train_and_evaluate(train: pd.DataFrame, test: pd.DataFrame, clean_mask: np.ndarray) -> dict:
    """Select a model by time-series CV, then score every candidate on the untouched holdout."""
    features = forecast_feature_names()
    X_train, y_train = train[features], train["target"]
    X_test, y_test = test[features], test["target"]

    rows, fitted, cv_oof = [], {}, {}
    for name, model in candidate_models().items():
        maes, oof_idx, oof_pred = _cv_scores(model, X_train, y_train)
        final = clone(model).fit(X_train, y_train)
        pred = final.predict(X_test)
        metrics = regression_metrics(y_test, pred)
        clean = regression_metrics(y_test[clean_mask], pred[clean_mask]) if clean_mask.any() else metrics
        rows.append(
            {
                "name": name,
                "cv_mae": float(maes.mean()),
                "cv_mae_std": float(maes.std()),
                "test_mae": metrics["mae"],
                "test_rmse": metrics["rmse"],
                "test_r2": metrics["r2"],
                "test_smape": metrics["smape"],
                "test_mae_clean": clean["mae"],
            }
        )
        fitted[name] = final
        cv_oof[name] = (oof_idx, oof_pred)

    learned = [r for r in rows if r["name"] not in ("Persistence", "Seasonal naive (24h)")]
    best = min(learned, key=lambda r: r["cv_mae"])["name"]
    best_model = fitted[best]
    pred = best_model.predict(X_test)

    oof_idx, oof_pred = cv_oof[best]
    oof = train.iloc[oof_idx].assign(pred=oof_pred)
    abs_res = (oof["target"] - oof["pred"]).abs()
    halfwidth = {zone: float(np.quantile(group, INTERVAL_COVERAGE)) for zone, group in abs_res.groupby(oof["zone"])}
    width = test["zone"].map(halfwidth).to_numpy()
    covered = (y_test.to_numpy() >= pred - width) & (y_test.to_numpy() <= pred + width)

    sample = X_test.sample(min(2000, len(X_test)), random_state=SEED)
    importance = permutation_importance(
        best_model,
        sample,
        y_test.loc[sample.index],
        n_repeats=4,
        random_state=SEED,
        scoring="neg_mean_absolute_error",
        n_jobs=-1,
    )

    return {
        "rows": rows,
        "best": best,
        "model": best_model,
        "pred": pred,
        "halfwidth": halfwidth,
        "coverage": float(covered.mean()),
        "importance": pd.Series(importance.importances_mean, index=features).sort_values(ascending=False),
        "all_predictions": {name: model.predict(X_test) for name, model in fitted.items()},
    }
