"""Runtime configuration, resolved from the environment with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ZONES = ["Downtown", "Industrial", "Residential", "Harbor", "University"]
DOMAINS = ("energy", "traffic", "air_quality", "weather")
DEFAULT_CORS = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:8080"


def _default_home() -> Path:
    """Repository root for a source checkout, otherwise the working directory."""
    root = Path(__file__).resolve().parents[2]
    return root if (root / "dataset").is_dir() else Path.cwd()


@dataclass(frozen=True)
class Settings:
    home: Path = field(default_factory=lambda: Path(os.environ.get("SMARTCITY_HOME", _default_home())))
    data_dir: Path | None = None
    db_path: Path | None = None
    model_dir: Path | None = None
    report_dir: Path | None = None
    figure_dir: Path | None = None
    cors_origins: str = field(default_factory=lambda: os.environ.get("SMARTCITY_CORS_ORIGINS", DEFAULT_CORS))
    api_key: str | None = field(default_factory=lambda: os.environ.get("SMARTCITY_API_KEY") or None)
    rate_limit_per_minute: int = field(default_factory=lambda: int(os.environ.get("SMARTCITY_RATE_LIMIT", "60")))
    trust_proxy: bool = field(default_factory=lambda: os.environ.get("SMARTCITY_TRUST_PROXY", "") == "1")

    def __post_init__(self) -> None:
        def resolve(value: Path | None, env: str, default: Path) -> Path:
            return Path(value or os.environ.get(env, default))

        object.__setattr__(self, "data_dir", resolve(self.data_dir, "SMARTCITY_DATA_DIR", self.home / "dataset"))
        object.__setattr__(self, "db_path", resolve(self.db_path, "SMARTCITY_DB", self.home / "var" / "smartcity.db"))
        object.__setattr__(
            self, "model_dir", resolve(self.model_dir, "SMARTCITY_MODEL_DIR", self.home / "var" / "models")
        )
        object.__setattr__(
            self, "report_dir", resolve(self.report_dir, "SMARTCITY_REPORT_DIR", self.home / "var" / "reports")
        )
        object.__setattr__(
            self, "figure_dir", resolve(self.figure_dir, "SMARTCITY_FIGURE_DIR", self.home / "docs" / "figures")
        )

    def csv_path(self, domain: str) -> Path:
        return self.data_dir / f"{domain}.csv"

    @property
    def labels_path(self) -> Path:
        return self.data_dir / "energy_anomaly_labels.csv"

    @property
    def metrics_path(self) -> Path:
        return self.report_dir / "metrics.json"
