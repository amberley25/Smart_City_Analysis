"""Command-line entry point: `smartcity simulate | ingest | train | all | serve`."""

from __future__ import annotations

import argparse
import logging

from . import db, pipeline, simulate
from .config import Settings


def _simulate(settings: Settings, args) -> None:
    sizes = simulate.write_dataset(settings, days=args.days, seed=args.seed)
    for name, rows in sizes.items():
        print(f"  {name:<24}{rows:>8,} rows")


def _ingest(settings: Settings, _args) -> None:
    for name, rows in db.ingest_csvs(settings).items():
        print(f"  {name:<24}{rows:>8,} rows -> {settings.db_path.name}")


def _train(settings: Settings, args) -> dict:
    from . import reporting

    artifacts = pipeline.run(settings)
    if not args.no_figures:
        for path in reporting.render_all(settings, artifacts):
            print(f"  wrote {path.relative_to(settings.home) if path.is_relative_to(settings.home) else path}")
    print(f"  metrics -> {settings.metrics_path}")
    return artifacts


def _all(settings: Settings, args) -> None:
    print("Simulating sensor network")
    _simulate(settings, args)
    print("Ingesting into SQLite")
    _ingest(settings, args)
    print("Training and evaluating models")
    _train(settings, args)


def _serve(settings: Settings, args) -> None:
    from .api import create_app

    create_app(settings).run(host=args.host, port=args.port, debug=args.debug)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="smartcity", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, func in {"simulate": _simulate, "all": _all}.items():
        p = sub.add_parser(name)
        p.add_argument("--days", type=int, default=120)
        p.add_argument("--seed", type=int, default=2026)
        p.add_argument("--no-figures", action="store_true")
        p.set_defaults(func=func)
    sub.add_parser("ingest").set_defaults(func=_ingest)
    p = sub.add_parser("train")
    p.add_argument("--no-figures", action="store_true")
    p.set_defaults(func=_train)
    p = sub.add_parser("serve")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=5000)
    p.add_argument("--debug", action="store_true")
    p.set_defaults(func=_serve)

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    args.func(Settings(), args)


if __name__ == "__main__":
    main()
