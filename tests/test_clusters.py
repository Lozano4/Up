"""Unit tests for the cluster filter, ranking and report. No network."""

from __future__ import annotations

from datetime import date, datetime

from cluster.clusters import confirm
from cluster.models import ClusterRow, Trade
from cluster.report import render

REPORT_DATE = date(2026, 10, 26)


def trade(ticker: str, insider: str, day: date, value: float, kind: str = "P - Purchase") -> Trade:
    return Trade(
        ticker=ticker,
        company=f"{ticker} Inc.",
        insider=insider,
        title="Dir",
        trade_type=kind,
        filing_time=datetime(day.year, day.month, day.day, 17, 0),
        trade_date=day,
        price=10.0,
        qty=int(value / 10),
        value=value,
        flags="",
    )


def row(ticker: str) -> ClusterRow:
    return ClusterRow(
        ticker=ticker,
        company=f"{ticker} Inc.",
        industry="Widgets",
        insiders=2,
        trade_type="P - Purchase",
        filing_time=datetime(2026, 10, 24, 17, 0),
        trade_date=date(2026, 10, 20),
        value=1.0,
    )


def test_keeps_two_unique_insiders_and_ranks() -> None:
    trades = [
        trade("AAA", "Smith John", date(2026, 10, 20), 50_000),
        trade("AAA", "Doe Jane", date(2026, 10, 21), 50_000),
        trade("BBB", "One A", date(2026, 10, 20), 10_000),
        trade("BBB", "Two B", date(2026, 10, 20), 10_000),
        trade("BBB", "Three C", date(2026, 10, 20), 10_000),
    ]
    kept, dropped = confirm([row("AAA"), row("BBB")], trades, REPORT_DATE)
    assert [c.ticker for c in kept] == ["BBB", "AAA"]  # 3 insiders beats more dollars
    assert dropped == []


def test_same_insider_twice_counts_once() -> None:
    trades = [
        trade("AAA", "Smith  John", date(2026, 10, 20), 50_000),
        trade("AAA", "SMITH JOHN", date(2026, 10, 22), 50_000),
    ]
    kept, dropped = confirm([row("AAA")], trades, REPORT_DATE)
    assert kept == []
    assert "only 1 insider" in dropped[0].reason


def test_ignores_non_purchase_codes_and_old_trades() -> None:
    trades = [
        trade("AAA", "Smith John", date(2026, 10, 20), 50_000),
        trade("AAA", "Doe Jane", date(2026, 10, 20), 50_000, kind="A - Grant"),
        trade("AAA", "Roe Rich", date(2026, 9, 26), 50_000),  # 31 days before, outside
    ]
    kept, dropped = confirm([row("AAA")], trades, REPORT_DATE)
    assert kept == []
    assert dropped[0].ticker == "AAA"


def test_window_edge_is_inclusive() -> None:
    trades = [
        trade("AAA", "Smith John", date(2026, 9, 27), 50_000),  # 30th day counting today
        trade("AAA", "Doe Jane", REPORT_DATE, 50_000),
    ]
    kept, _ = confirm([row("AAA")], trades, REPORT_DATE)
    assert [c.ticker for c in kept] == ["AAA"]


def test_report_lists_ranked_and_dropped() -> None:
    trades = [
        trade("AAA", "Smith John", date(2026, 10, 20), 50_000),
        trade("AAA", "Doe Jane", date(2026, 10, 21), 25_000),
    ]
    kept, dropped = confirm([row("AAA"), row("ZZZ")], trades, REPORT_DATE)
    text = render(kept, dropped, REPORT_DATE, datetime(2026, 10, 26, 6, 0))
    assert "# Insider cluster buys, 2026-10-26" in text
    assert "| 1 | [AAA](http://openinsider.com/AAA) | AAA Inc. | 2 | 2 | $75,000 |" in text
    assert "[ZZZ](http://openinsider.com/ZZZ) (ZZZ Inc.): no open-market purchases" in text
