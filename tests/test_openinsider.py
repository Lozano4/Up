"""Unit tests for OpenInsider page parsing. No network."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from cluster import config
from cluster.openinsider import (
    FetchError,
    parse_cluster_rows,
    parse_number,
    parse_table,
    parse_trades,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("$44.17", 44.17),
        ("+11,900", 11_900.0),
        ("+$525,575", 525_575.0),
        ("-$1,234", -1_234.0),
        ("", 0.0),
    ],
)
def test_parse_number(raw: str, expected: float) -> None:
    assert parse_number(raw) == pytest.approx(expected)


def test_parse_number_rejects_garbage() -> None:
    with pytest.raises(FetchError):
        parse_number("n/a")


def test_parse_cluster_page() -> None:
    rows = parse_cluster_rows((FIXTURES / "cluster_page.html").read_text(encoding="utf-8"))
    assert len(rows) == 4
    first = rows[0]
    assert first.ticker == "NXG"
    assert first.insiders == 3
    assert first.trade_type == "P - Purchase"
    assert first.trade_date == date(2026, 10, 19)
    assert first.value == pytest.approx(525_575.0)


def test_parse_trades_page() -> None:
    trades = parse_trades((FIXTURES / "trades_page.html").read_text(encoding="utf-8"))
    assert len(trades) == 6
    first = trades[0]
    assert first.ticker == "NMHI"
    assert first.insider == "Adair Kathleen Theresa"
    assert first.code == "P"
    assert first.qty == 11_600_000
    assert first.flags == "M"


def test_missing_table_fails_loudly() -> None:
    with pytest.raises(FetchError, match="no results table"):
        parse_table("<html><body>Too many requests</body></html>", config.TRADES_HEADER)


def test_changed_header_fails_loudly() -> None:
    html = (FIXTURES / "cluster_page.html").read_text(encoding="utf-8")
    with pytest.raises(FetchError, match="unexpected table header"):
        parse_table(html, config.TRADES_HEADER)
