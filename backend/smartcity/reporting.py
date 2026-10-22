"""Static evaluation and EDA figures (written to docs/figures and embedded in the README)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from . import db  # noqa: E402
from .config import ZONES, Settings  # noqa: E402

INK = "#1f2933"
MUTED = "#6b7785"
GRID = "#e4e8ec"
BLUE = "#2c5f8a"
BLUE_SOFT = "#a9c4dc"
ORANGE = "#d1752b"
GREY = "#a4adb7"
TEAL = "#3b8c86"
ZONE_COLORS = ["#2c5f8a", "#d1752b", "#3b8c86", "#7b5ea7", "#9a8b2c"]

BASELINES = {"Persistence", "Seasonal naive (24h)"}


def _style() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 100,
            "savefig.dpi": 160,
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.titlecolor": INK,
            "axes.titlelocation": "left",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.7,
            "axes.axisbelow": True,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "legend.frameon": False,
            "legend.fontsize": 8.5,
            "figure.facecolor": "white",
        }
    )


def _save(fig, settings: Settings, name: str) -> Path:
    settings.figure_dir.mkdir(parents=True, exist_ok=True)
    path = settings.figure_dir / name
    fig.savefig(path, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _bar_labels(ax, bars, fmt="{:.1f}", pad=0.01):
    span = ax.get_xlim()[1]
    for bar in bars:
        ax.text(
            bar.get_width() + span * pad,
            bar.get_y() + bar.get_height() / 2,
            fmt.format(bar.get_width()),
            va="center",
            fontsize=8.5,
            color=INK,
        )


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------


def forecast_comparison(settings, metrics) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.6), sharex=False)
    for ax, horizon in zip(axes, ("1", "24"), strict=True):
        block = metrics["forecast"][horizon]
        rows = sorted(block["models"], key=lambda r: -r["test_mae"])
        colors = [
            GREY if r["name"] in BASELINES else (BLUE if r["name"] == block["best_model"] else BLUE_SOFT) for r in rows
        ]
        bars = ax.barh([r["name"] for r in rows], [r["test_mae"] for r in rows], color=colors, height=0.62)
        ax.set_xlim(0, max(r["test_mae"] for r in rows) * 1.3)
        span = ax.get_xlim()[1]
        for bar, r in zip(bars, rows, strict=True):
            ax.text(
                bar.get_width() + span * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"{r['test_mae']:.1f}  (CV {r['cv_mae']:.1f})",
                va="center",
                fontsize=8.5,
                color=INK,
            )
        ax.set_title(f"{horizon}-hour-ahead forecast")
        ax.set_xlabel("Mean absolute error on holdout (kWh)")
        ax.grid(axis="y", visible=False)
    fig.suptitle(
        "Forecast accuracy by model (lower is better)",
        x=0.01,
        ha="left",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        y=1.04,
    )
    return _save(fig, settings, "forecast_model_comparison.png")


def forecast_backtest(settings, metrics) -> Path:
    block = metrics["forecast"]["1"]["backtest"]
    frame = pd.DataFrame(block)
    frame["timestamp"] = pd.to_datetime(frame["timestamp"])
    fig, axes = plt.subplots(len(ZONES), 1, figsize=(11, 8.6), sharex=True)
    for ax, zone in zip(axes, ZONES, strict=True):
        part = frame[frame["zone"] == zone]
        ax.fill_between(
            part["timestamp"],
            part["lower"],
            part["upper"],
            color=BLUE_SOFT,
            alpha=0.55,
            linewidth=0,
            label="90% interval",
        )
        ax.plot(part["timestamp"], part["actual"], color=INK, linewidth=1.3, label="Actual")
        ax.plot(
            part["timestamp"], part["predicted"], color=BLUE, linewidth=1.3, linestyle=(0, (4, 2)), label="Forecast"
        )
        ax.set_title(zone, fontsize=9.5, pad=4)
        ax.tick_params(axis="y", labelsize=8)
    axes[2].set_ylabel("Energy (kWh)")
    axes[0].legend(ncol=3, loc="lower right", bbox_to_anchor=(1, 1.0))
    fig.suptitle(
        "Holdout week: 1-hour-ahead energy forecast against actual",
        x=0.01,
        ha="left",
        fontsize=12.5,
        fontweight="bold",
        color=INK,
        y=0.995,
    )
    fig.tight_layout(h_pad=1.2)
    axes[-1].xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%a %d %b"))
    return _save(fig, settings, "forecast_backtest.png")


def forecast_diagnostics(settings, metrics) -> Path:
    h1, h24 = metrics["forecast"]["1"], metrics["forecast"]["24"]
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    ax = axes[0, 0]
    pts = np.array(h1["scatter"])
    lim = (0, max(pts.max() * 1.03, 1))
    ax.scatter(pts[:, 0], pts[:, 1], s=9, color=BLUE, alpha=0.35, linewidth=0)
    ax.plot(lim, lim, color=ORANGE, linewidth=1.2, label="Perfect forecast")
    best = next(r for r in h1["models"] if r["name"] == h1["best_model"])
    ax.text(
        0.04,
        0.93,
        f"R² = {best['test_r2']:.3f}\nMAE = {best['test_mae']:.1f} kWh",
        transform=ax.transAxes,
        va="top",
        fontsize=9.5,
        color=INK,
    )
    ax.set(
        xlim=lim,
        ylim=lim,
        xlabel="Actual (kWh)",
        ylabel="Forecast (kWh)",
        title="Forecast against actual, 1 hour ahead",
    )
    ax.legend(loc="lower right")

    ax = axes[0, 1]
    res = h1["residual_histogram"]
    edges = np.array(res["edges"])
    ax.bar(edges[:-1], res["counts"], width=np.diff(edges), align="edge", color=BLUE, alpha=0.85, linewidth=0)
    ax.axvline(0, color=ORANGE, linewidth=1.2)
    ax.set(xlabel="Actual minus forecast (kWh)", ylabel="Hours", title="Error distribution, 1 hour ahead")

    ax = axes[1, 0]
    for block, label, color in ((h1, "1 hour ahead", BLUE), (h24, "24 hours ahead", ORANGE)):
        hours = sorted(block["mae_by_hour"], key=int)
        ax.plot(
            [int(h) for h in hours], [block["mae_by_hour"][h] for h in hours], color=color, linewidth=1.8, label=label
        )
    ax.set(xlabel="Hour of day", ylabel="MAE (kWh)", title="Error by hour of day", xticks=range(0, 24, 3))
    ax.legend()

    ax = axes[1, 1]
    top = h1["feature_importance"][:10][::-1]
    bars = ax.barh([t["feature"] for t in top], [t["importance"] for t in top], color=BLUE, height=0.62)
    ax.set_xlim(0, max(t["importance"] for t in top) * 1.2)
    _bar_labels(ax, bars, "{:.1f}")
    ax.set(xlabel="Increase in MAE when shuffled (kWh)", title="What the model relies on")
    ax.grid(axis="y", visible=False)

    fig.tight_layout(h_pad=2.4, w_pad=2.4)
    return _save(fig, settings, "forecast_diagnostics.png")


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------

METHOD_COLORS = {0: BLUE, 1: GREY, 2: ORANGE}
SHORT = {
    "Isolation forest (engineered features)": "Isolation forest, engineered",
    "Isolation forest (raw readings)": "Isolation forest, raw readings",
    "Robust z-score (energy only)": "Robust z-score",
}


def anomaly_benchmark(settings, metrics) -> Path:
    block = metrics["anomaly"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))
    for i, method in enumerate(block["methods"]):
        curves = block["curves"][method["name"]]
        roc, pr = np.array(curves["roc"]), np.array(curves["pr"])
        label = f"{SHORT[method['name']]} (AUC {method['roc_auc']:.2f})"
        axes[0].plot(roc[:, 0], roc[:, 1], color=METHOD_COLORS[i], linewidth=1.8, label=label)
        axes[1].plot(
            pr[:, 0],
            pr[:, 1],
            color=METHOD_COLORS[i],
            linewidth=1.8,
            label=f"{SHORT[method['name']]} (AP {method['pr_auc']:.2f})",
        )
    axes[0].plot([0, 1], [0, 1], color=GRID, linewidth=1.2, linestyle="--")
    axes[0].set(
        xlabel="False positive rate", ylabel="True positive rate", title="ROC curve", xlim=(0, 1), ylim=(0, 1.02)
    )
    axes[1].set(xlabel="Recall", ylabel="Precision", title="Precision-recall curve", xlim=(0, 1), ylim=(0, 1.02))
    for ax in axes[:2]:
        ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), fontsize=8)

    ax = axes[2]
    names = [SHORT[m["name"]].replace(", ", ",\n").replace("Robust ", "Robust\n") for m in block["methods"]]
    x = np.arange(len(names))
    width = 0.26
    for j, (key, label, color) in enumerate(
        (("precision", "Precision", BLUE_SOFT), ("recall", "Recall", BLUE), ("f1", "F1", ORANGE))
    ):
        ax.bar(x + (j - 1) * width, [m[key] for m in block["methods"]], width, label=label, color=color)
    ax.set_xticks(x, names, fontsize=7.3)
    ax.set(ylim=(0, 1.08), title=f"At a {block['alert_rate'] * 100:.1f}% alert budget")
    ax.grid(axis="x", visible=False)
    ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, 1.02), fontsize=8)
    fig.tight_layout(w_pad=2.2)
    return _save(fig, settings, "anomaly_benchmark.png")


def anomaly_detail(settings, metrics, artifacts) -> Path:
    block = metrics["anomaly"]
    primary = block["methods"][0]
    cm = primary["confusion"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))

    ax = axes[0]
    matrix = np.array([[cm["tn"], cm["fp"]], [cm["fn"], cm["tp"]]])
    share = matrix / matrix.sum(axis=1, keepdims=True)
    ax.imshow(
        share, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("m", ["#ffffff", BLUE]), vmin=0, vmax=1.25
    )
    for (i, j), value in np.ndenumerate(matrix):
        ax.text(
            j,
            i,
            f"{value:,}\n{share[i, j] * 100:.1f}%",
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white" if share[i, j] > 0.5 else INK,
        )
    ax.set_xticks([0, 1], ["Normal", "Flagged"])
    ax.set_yticks([0, 1], ["Normal", "Anomaly"])
    ax.set(xlabel="Detector output", ylabel="Ground truth", title="Confusion matrix (holdout)")
    ax.grid(False)

    ax = axes[1]
    types = block["per_type"]
    labels = [t["type"].replace("_", " ") for t in types]
    bars = ax.barh(labels, [t["recall"] or 0 for t in types], color=BLUE, height=0.55)
    ax.set_xlim(0, 1.22)
    for bar, t in zip(bars, types, strict=True):
        ax.text(
            bar.get_width() + 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{(t['recall'] or 0) * 100:.0f}%  (n={t['count']})",
            va="center",
            fontsize=8.5,
            color=INK,
        )
    ax.invert_yaxis()
    ax.set(xlabel="Recall", title="Detection rate by fault type")
    ax.grid(axis="y", visible=False)

    ax = axes[2]
    a = artifacts["anomaly"]
    truth = artifacts["anomaly_frames"]["test"]["truth"].to_numpy()
    score = a["test_scores"]
    bins = np.linspace(score.min(), score.max(), 45)
    ax.hist(score[~truth], bins=bins, color=BLUE_SOFT, label="Normal", log=True)
    ax.hist(score[truth], bins=bins, color=ORANGE, alpha=0.85, label="Anomaly", log=True)
    ax.axvline(primary["threshold"], color=INK, linestyle="--", linewidth=1.2)
    ax.text(primary["threshold"] + 0.004, 1.3, "alert threshold", fontsize=8, color=INK, rotation=90, va="bottom")
    ax.set(xlabel="Anomaly score", ylabel="Readings (log scale)", title="Score separation")
    ax.legend(loc="center right")
    fig.tight_layout(w_pad=2.2)
    return _save(fig, settings, "anomaly_detail.png")


def anomaly_timeline(settings, artifacts) -> Path:
    frames = artifacts["anomaly_frames"]
    test = frames["test"].copy()
    test["flagged"] = artifacts["anomaly"]["test_flagged"]
    zone = test[test["truth"]].groupby("zone").size().idxmax()
    part = test[test["zone"] == zone].sort_values("timestamp")
    fig, ax = plt.subplots(figsize=(11.5, 3.8))
    ax.plot(part["timestamp"], part["energy_kwh"], color=INK, linewidth=1.0)
    truth = part[part["truth"]]
    ax.scatter(
        truth["timestamp"],
        truth["energy_kwh"],
        s=70,
        facecolors="none",
        edgecolors=ORANGE,
        linewidth=1.4,
        label="Injected fault (ground truth)",
    )
    hits = part[part["flagged"]]
    ax.scatter(hits["timestamp"], hits["energy_kwh"], s=14, color=BLUE, zorder=3, label="Flagged by detector")
    ax.set(ylabel="Energy (kWh)", title=f"{zone}: detections over the 28-day holdout")
    ax.legend(loc="lower right", ncol=2, bbox_to_anchor=(1, 1.0))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%d %b"))
    return _save(fig, settings, "anomaly_timeline.png")


# ---------------------------------------------------------------------------
# Exploratory analysis
# ---------------------------------------------------------------------------


def eda_profiles(settings, energy) -> Path:
    energy = energy.copy()
    energy["hour"] = energy["timestamp"].dt.hour
    energy["daytype"] = np.where(energy["timestamp"].dt.dayofweek >= 5, "Weekend", "Weekday")
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.7), sharey=True)
    for ax, daytype in zip(axes, ("Weekday", "Weekend"), strict=True):
        sub = energy[energy["daytype"] == daytype]
        for zone, color in zip(ZONES, ZONE_COLORS, strict=True):
            z = sub[sub["zone"] == zone]
            curve = z.groupby("hour")["energy_kwh"].median()
            ax.plot(curve.index, curve / curve.mean(), color=color, linewidth=1.8, label=zone)
        ax.set(title=f"{daytype} demand profile", xlabel="Hour of day", xticks=range(0, 24, 3))
    axes[0].set_ylabel("Median demand / zone mean")
    axes[1].legend(ncol=1, loc="upper left", bbox_to_anchor=(1.01, 1))
    return _save(fig, settings, "eda_daily_profiles.png")


def eda_relationships(settings, frames) -> Path:
    energy, weather, traffic, air = frames["energy"], frames["weather"], frames["traffic"], frames["air_quality"]
    fig, axes = plt.subplots(1, 3, figsize=(12.5, 3.9))

    daily = (
        energy[energy["zone"] == "Residential"][["timestamp", "energy_kwh"]]
        .merge(weather[weather["zone"] == "Residential"][["timestamp", "temperature_c"]], on="timestamp")
        .assign(day=lambda d: d["timestamp"].dt.floor("D"))
        .groupby("day")
        .agg(energy=("energy_kwh", "mean"), temp=("temperature_c", "mean"))
        .dropna()
    )
    axes[0].scatter(daily["temp"], daily["energy"], s=22, color=BLUE, alpha=0.75, linewidth=0)
    slope, intercept = np.polyfit(daily["temp"], daily["energy"], 1)
    xs = np.linspace(daily["temp"].min(), daily["temp"].max(), 20)
    axes[0].plot(xs, slope * xs + intercept, color=ORANGE, linewidth=1.5)
    r = np.corrcoef(daily["temp"], daily["energy"])[0, 1]
    axes[0].text(0.96, 0.95, f"r = {r:.2f}", transform=axes[0].transAxes, ha="right", va="top")
    axes[0].set(
        xlabel="Daily mean temperature (°C)", ylabel="Mean demand (kWh)", title="Residential demand vs temperature"
    )

    merged = (
        traffic[["zone", "timestamp", "traffic_count"]]
        .merge(air[["zone", "timestamp", "pm25_ugm3"]], on=["zone", "timestamp"])
        .dropna()
    )
    sub = merged[merged["zone"] == "Downtown"].sample(1500, random_state=1)
    axes[1].scatter(sub["traffic_count"], sub["pm25_ugm3"], s=8, color=TEAL, alpha=0.4, linewidth=0)
    r = np.corrcoef(sub["traffic_count"], sub["pm25_ugm3"])[0, 1]
    axes[1].text(0.04, 0.95, f"r = {r:.2f}", transform=axes[1].transAxes, va="top")
    axes[1].set(xlabel="Vehicles per hour", ylabel="PM2.5 (µg/m³)", title="Downtown traffic vs PM2.5")

    keys = ["zone", "timestamp"]
    wx = (
        weather[[*keys, "temperature_c", "wind_speed_ms", "precipitation_mm"]]
        .merge(air[[*keys, "pm25_ugm3", "no2_ppb"]], on=keys)
        .merge(traffic[[*keys, "traffic_count"]], on=keys)
        .merge(energy[[*keys, "energy_kwh"]], on=keys)
    )
    cols = {
        "temperature_c": "Temperature",
        "wind_speed_ms": "Wind",
        "precipitation_mm": "Rain",
        "traffic_count": "Traffic",
        "pm25_ugm3": "PM2.5",
        "no2_ppb": "NO2",
        "energy_kwh": "Energy",
    }
    z = wx.groupby("zone")[list(cols)].transform(lambda s: (s - s.mean()) / s.std())
    corr = z.corr().to_numpy()
    im = axes[2].imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    axes[2].set_xticks(range(len(cols)), list(cols.values()), rotation=45, ha="right", fontsize=8)
    axes[2].set_yticks(range(len(cols)), list(cols.values()), fontsize=8)
    axes[2].grid(False)
    for (i, j), value in np.ndenumerate(corr):
        axes[2].text(
            j, i, f"{value:.1f}", ha="center", va="center", fontsize=7, color="white" if abs(value) > 0.6 else INK
        )
    axes[2].set_title("Within-zone correlation")
    fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.03)
    fig.tight_layout(w_pad=2)
    return _save(fig, settings, "eda_relationships.png")


def eda_data_quality(settings, frames) -> Path:
    names = {"energy": "Energy", "traffic": "Traffic", "air_quality": "Air quality", "weather": "Weather"}
    fig, ax = plt.subplots(figsize=(8.5, 3.2))
    status = {n: frames[d]["status"].value_counts(normalize=True) * 100 for d, n in names.items()}
    table = pd.DataFrame(status).fillna(0).T[["OK", "DEGRADED", "OFFLINE"]]
    left = np.zeros(len(table))
    for column, color in zip(table.columns, (BLUE, ORANGE, GREY), strict=True):
        ax.barh(table.index, table[column], left=left, color=color, label=column.title(), height=0.55)
        left += table[column].to_numpy()
    ax.set(xlim=(94, 100.1), xlabel="Share of readings (%)", title="Sensor status by network")
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.legend(ncol=3, loc="lower left", bbox_to_anchor=(0, -0.42))
    return _save(fig, settings, "eda_data_quality.png")


def render_all(settings: Settings, artifacts: dict) -> list[Path]:
    _style()
    metrics = artifacts["metrics"]
    frames = {d: db.read_frame(settings, d) for d in db.MEASURES}
    return [
        forecast_comparison(settings, metrics),
        forecast_backtest(settings, metrics),
        forecast_diagnostics(settings, metrics),
        anomaly_benchmark(settings, metrics),
        anomaly_detail(settings, metrics, artifacts),
        anomaly_timeline(settings, artifacts),
        eda_profiles(settings, frames["energy"]),
        eda_relationships(settings, frames),
        eda_data_quality(settings, frames),
    ]
