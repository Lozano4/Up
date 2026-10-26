"""Command-line entry point: ``python -m cluster <command>``.

Commands: fetch, report, run-all.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Sequence
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cluster import __version__, config
from cluster.clusters import confirm
from cluster.models import ClusterRow, Trade, load_csv, save_csv
from cluster.openinsider import FetchError, fetch_clusters, fetch_trades, new_session
from cluster.report import render, write_report

log = logging.getLogger("cluster")

EXIT_OK = 0
EXIT_FAILED = 1


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser with one sub-command per step."""
    parser = argparse.ArgumentParser(
        prog="python -m cluster",
        description="Insider cluster buys report (read-only, never trades).",
    )
    parser.add_argument("--version", action="version", version=f"insider-cluster {__version__}")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="log at DEBUG level instead of INFO"
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>", required=True)
    sub.add_parser("fetch", help="fetch cluster buys and purchases to data/")
    sub.add_parser("report", help="confirm, rank, and write reports/<date>.md and latest.md")
    sub.add_parser("run-all", help="fetch, then report")
    return parser


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def now_pacific() -> datetime:
    return datetime.now(ZoneInfo(config.REPORT_TIMEZONE))


def data_paths(day: date) -> tuple[Path, Path]:
    stamp = day.isoformat()
    return config.CLUSTERS_DIR / f"{stamp}.csv", config.TRADES_DIR / f"{stamp}.csv"


def cmd_fetch() -> int:
    """Fetch both pages; save nothing unless both succeed."""
    clusters_path, trades_path = data_paths(now_pacific().date())
    try:
        session = new_session()
        rows = fetch_clusters(session)
        trades = fetch_trades(session)
    except FetchError as err:
        log.error("fetch failed, nothing saved: %s", err)
        return EXIT_FAILED
    save_csv(rows, ClusterRow, clusters_path)
    save_csv(trades, Trade, trades_path)
    log.info("saved %s and %s", clusters_path.name, trades_path.name)
    return EXIT_OK


def cmd_report() -> int:
    """Build today's report from today's fetched data."""
    generated = now_pacific()
    report_date = generated.date()
    clusters_path, trades_path = data_paths(report_date)
    missing = [p for p in (clusters_path, trades_path) if not p.exists()]
    if missing:
        log.error("no data for %s (missing %s); run fetch first", report_date, missing[0])
        return EXIT_FAILED
    rows = load_csv(ClusterRow, clusters_path)
    trades = load_csv(Trade, trades_path)
    kept, dropped = confirm(rows, trades, report_date)
    path = write_report(render(kept, dropped, report_date, generated), report_date)
    log.info("report: %d confirmed, %d dropped -> %s", len(kept), len(dropped), path.name)
    return EXIT_OK


def cmd_run_all() -> int:
    """Fetch, then report; stop at the first failure."""
    for name, func in (("fetch", cmd_fetch), ("report", cmd_report)):
        code = func()
        if code != EXIT_OK:
            log.error("run-all stopped at %r with exit code %d", name, code)
            return code
    return EXIT_OK


HANDLERS: dict[str, Callable[[], int]] = {
    "fetch": cmd_fetch,
    "report": cmd_report,
    "run-all": cmd_run_all,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Parse arguments, dispatch, and return the process exit code."""
    args = build_parser().parse_args(argv)
    configure_logging(args.verbose)
    log.info("insider-cluster %s: running %r", __version__, args.command)
    return HANDLERS[args.command]()


if __name__ == "__main__":
    sys.exit(main())
