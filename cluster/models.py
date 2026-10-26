"""Dataclasses passed between modules, plus CSV save and load for them."""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, fields
from datetime import date, datetime
from pathlib import Path
from typing import TypeVar


@dataclass(frozen=True)
class ClusterRow:
    """One row of OpenInsider's latest cluster buys page."""

    ticker: str
    company: str
    industry: str
    insiders: int
    trade_type: str
    filing_time: datetime
    trade_date: date
    value: float


@dataclass(frozen=True)
class Trade:
    """One insider trade from the OpenInsider screener."""

    ticker: str
    company: str
    insider: str
    title: str
    trade_type: str
    filing_time: datetime
    trade_date: date
    price: float
    qty: int
    value: float
    flags: str

    @property
    def code(self) -> str:
        """The SEC transaction code, e.g. "P" from "P - Purchase"."""
        return self.trade_type.split("-", 1)[0].strip()


@dataclass(frozen=True)
class Cluster:
    """A ticker that passed the filter, with its qualifying buys."""

    ticker: str
    company: str
    industry: str
    trades: tuple[Trade, ...]

    @property
    def insiders(self) -> tuple[str, ...]:
        """Unique insider names, in the order first seen."""
        seen: dict[str, str] = {}
        for trade in self.trades:
            seen.setdefault(insider_key(trade.insider), trade.insider)
        return tuple(seen.values())

    @property
    def total_value(self) -> float:
        return sum(trade.value for trade in self.trades)

    @property
    def first_trade(self) -> date:
        return min(trade.trade_date for trade in self.trades)

    @property
    def last_trade(self) -> date:
        return max(trade.trade_date for trade in self.trades)

    @property
    def last_filing(self) -> datetime:
        return max(trade.filing_time for trade in self.trades)


@dataclass(frozen=True)
class Dropped:
    """A ticker from the cluster page that did not pass, and why."""

    ticker: str
    company: str
    reason: str


def insider_key(name: str) -> str:
    """Normalize an insider name so the same person is counted once."""
    return " ".join(name.split()).casefold()


Row = TypeVar("Row", ClusterRow, Trade)


def save_csv(rows: list[Row], row_type: type[Row], path: Path) -> None:
    """Write dataclass rows to CSV, through a temp file so a crash leaves no half file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    names = [f.name for f in fields(row_type)]
    with tmp.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=names)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _to_text(v) for k, v in asdict(row).items()})
    tmp.replace(path)


def load_csv(row_type: type[Row], path: Path) -> list[Row]:
    """Read rows written by save_csv back into dataclasses."""
    with path.open(newline="", encoding="utf-8") as handle:
        return [_from_text(row_type, raw) for raw in csv.DictReader(handle)]


def _to_text(value: object) -> str:
    if isinstance(value, datetime):
        return value.isoformat(sep=" ")
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _from_text(row_type: type[Row], raw: dict[str, str]) -> Row:
    converters = {
        "insiders": int,
        "qty": int,
        "price": float,
        "value": float,
        "filing_time": datetime.fromisoformat,
        "trade_date": date.fromisoformat,
    }
    values = {f.name: converters.get(f.name, str)(raw[f.name]) for f in fields(row_type)}
    return row_type(**values)
