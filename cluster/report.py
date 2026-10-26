"""Render the ranked Markdown report."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from cluster import config
from cluster.clusters import window_start
from cluster.models import Cluster, Dropped


def render(
    clusters: list[Cluster], dropped: list[Dropped], report_date: date, generated: datetime
) -> str:
    """Build the whole report as one Markdown string."""
    start = window_start(report_date)
    lines = [
        f"# Insider cluster buys, {report_date.isoformat()}",
        "",
        f"Generated {generated:%Y-%m-%d %H:%M} Pacific. Trade dates {start.isoformat()} to "
        f"{report_date.isoformat()}. Open-market purchases (code P) only, "
        f"{config.MIN_UNIQUE_INSIDERS}+ different insiders per company.",
        "",
        f"**{len(clusters)} confirmed** out of {len(clusters) + len(dropped)} on OpenInsider's "
        "latest cluster buys page.",
        "",
        "Read-only research. Nothing here is an order or a recommendation.",
        "",
    ]
    lines += _ranked_table(clusters)
    lines += _details(clusters)
    lines += _dropped(dropped)
    return "\n".join(lines).rstrip() + "\n"


def _ranked_table(clusters: list[Cluster]) -> list[str]:
    lines = ["## Ranked", ""]
    if not clusters:
        return lines + ["None today.", ""]
    lines += [
        "| # | Ticker | Company | Insiders | Buys | Total value | First trade | Last trade "
        "| Latest filing |",
        "|---:|---|---|---:|---:|---:|---|---|---|",
    ]
    for rank, c in enumerate(clusters, start=1):
        lines.append(
            f"| {rank} | {_ticker_link(c.ticker)} | {_cell(c.company)} | {len(c.insiders)} "
            f"| {len(c.trades)} | {_money(c.total_value)} | {c.first_trade} | {c.last_trade} "
            f"| {c.last_filing:%Y-%m-%d} |"
        )
    return lines + [""]


def _details(clusters: list[Cluster]) -> list[str]:
    lines: list[str] = []
    for rank, c in enumerate(clusters, start=1):
        lines += [
            f"## {rank}. {c.ticker}, {c.company}",
            "",
            f"{c.industry}. {len(c.insiders)} insiders, {_money(c.total_value)} total.",
            "",
            "| Insider | Title | Trade date | Price | Shares | Value |",
            "|---|---|---|---:|---:|---:|",
        ]
        for t in c.trades:
            lines.append(
                f"| {_cell(t.insider)} | {_cell(t.title)} | {t.trade_date} | ${t.price:,.2f} "
                f"| {t.qty:,} | {_money(t.value)} |"
            )
        lines.append("")
    return lines


def _dropped(dropped: list[Dropped]) -> list[str]:
    lines = ["## Dropped", ""]
    if not dropped:
        return lines + ["None.", ""]
    lines += [f"- {_ticker_link(d.ticker)} ({_cell(d.company)}): {d.reason}" for d in dropped]
    return lines + [""]


def _ticker_link(ticker: str) -> str:
    return f"[{ticker}]({config.OPENINSIDER_BASE}/{ticker})"


def _money(value: float) -> str:
    return f"${value:,.0f}"


def _cell(text: str) -> str:
    """Keep a pipe in a name from breaking the table."""
    return text.replace("|", "\\|")


def write_report(text: str, report_date: date) -> Path:
    """Write the dated report and latest.md, each through a temp file."""
    config.REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dated = config.REPORTS_DIR / f"{report_date.isoformat()}.md"
    for path in (dated, config.LATEST_REPORT):
        tmp = path.with_suffix(".tmp")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)
    return dated
