"""Confirm each cluster against the individual trades, then rank the ones that pass."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from cluster import config
from cluster.models import Cluster, ClusterRow, Dropped, Trade, insider_key


def window_start(report_date: date) -> date:
    """First trade date that counts: the window is WINDOW_DAYS days ending on report_date."""
    return report_date - timedelta(days=config.WINDOW_DAYS - 1)


def qualifying(trades: list[Trade], report_date: date) -> list[Trade]:
    """Open-market purchases (code P) with a trade date inside the window."""
    start = window_start(report_date)
    return [
        trade
        for trade in trades
        if trade.code == config.PURCHASE_CODE and start <= trade.trade_date <= report_date
    ]


def confirm(
    rows: list[ClusterRow], trades: list[Trade], report_date: date
) -> tuple[list[Cluster], list[Dropped]]:
    """Split the cluster page's tickers into confirmed clusters (ranked) and dropped ones."""
    by_ticker: dict[str, list[Trade]] = defaultdict(list)
    for trade in qualifying(trades, report_date):
        by_ticker[trade.ticker].append(trade)

    kept: list[Cluster] = []
    dropped: list[Dropped] = []
    for row in _unique_tickers(rows):
        buys = by_ticker.get(row.ticker, [])
        reason = _drop_reason(buys)
        if reason:
            dropped.append(Dropped(ticker=row.ticker, company=row.company, reason=reason))
        else:
            ordered = tuple(sorted(buys, key=lambda t: (t.trade_date, t.insider)))
            kept.append(Cluster(row.ticker, row.company, row.industry, ordered))
    return rank(kept), sorted(dropped, key=lambda d: d.ticker)


def rank(clusters: list[Cluster]) -> list[Cluster]:
    """Most unique insiders first, then largest total value, then ticker A to Z."""
    return sorted(clusters, key=lambda c: (-len(c.insiders), -c.total_value, c.ticker))


def _drop_reason(buys: list[Trade]) -> str | None:
    if not buys:
        return f"no open-market purchases (code P) in the last {config.WINDOW_DAYS} days"
    unique = {insider_key(trade.insider) for trade in buys}
    if len(unique) < config.MIN_UNIQUE_INSIDERS:
        return f"only {len(unique)} insider bought in the last {config.WINDOW_DAYS} days"
    return None


def _unique_tickers(rows: list[ClusterRow]) -> list[ClusterRow]:
    """The cluster page can list a ticker more than once; keep the first (newest) row."""
    seen: dict[str, ClusterRow] = {}
    for row in rows:
        seen.setdefault(row.ticker, row)
    return list(seen.values())
