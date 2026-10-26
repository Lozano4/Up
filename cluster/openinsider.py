"""Fetch and parse OpenInsider's cluster buys page and purchase screener."""

from __future__ import annotations

import logging
import time
from datetime import date, datetime
from html.parser import HTMLParser

import requests

from cluster import config
from cluster.models import ClusterRow, Trade

log = logging.getLogger(__name__)


class FetchError(RuntimeError):
    """A page could not be fetched or did not look like we expect."""


class _TinyTableParser(HTMLParser):
    """Collect the header and the cell text of the first table with class "tinytable"."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.header: list[str] = []
        self.rows: list[list[str]] = []
        self._depth = 0  # table nesting depth inside the tinytable, 0 = outside
        self._done = False
        self._cell: list[str] | None = None
        self._row: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._done:
            return
        if tag == "table":
            classes = (dict(attrs).get("class") or "").split()
            if self._depth or "tinytable" in classes:
                self._depth += 1
        elif self._depth and tag == "tr":
            self._row = []
        elif self._depth and tag in ("td", "th"):
            self._cell = []

    def handle_endtag(self, tag: str) -> None:
        if not self._depth or self._done:
            return
        if tag == "table":
            self._depth -= 1
            self._done = self._depth == 0
        elif tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            self._store_row(self._row)
            self._row = None

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def _store_row(self, row: list[str]) -> None:
        if not self.header:
            self.header = row
        elif row:
            self.rows.append(row)


def parse_table(html: str, expected_header: tuple[str, ...]) -> list[dict[str, str]]:
    """Return the tinytable's rows as dicts keyed by header, after checking the header."""
    parser = _TinyTableParser()
    parser.feed(html)
    if not parser.header:
        raise FetchError("no results table found; OpenInsider may have changed its page")
    if tuple(parser.header) != expected_header:
        raise FetchError(f"unexpected table header {parser.header}; expected {expected_header}")
    width = len(expected_header)
    bad = [row for row in parser.rows if len(row) != width]
    if bad:
        raise FetchError(f"{len(bad)} rows do not have {width} cells, first: {bad[0]}")
    return [dict(zip(expected_header, row, strict=True)) for row in parser.rows]


def parse_number(raw: str) -> float:
    """Parse "$44.17", "+11,900", "-$1,234" into a float. Blank means 0."""
    text = raw.replace("$", "").replace(",", "").replace("+", "").strip()
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError as err:
        raise FetchError(f"cannot read number {raw!r}") from err


def parse_cluster_rows(html: str) -> list[ClusterRow]:
    """Parse the latest cluster buys page."""
    return [
        ClusterRow(
            ticker=row["Ticker"],
            company=row["Company Name"],
            industry=row["Industry"],
            insiders=int(parse_number(row["Ins"])),
            trade_type=row["Trade Type"],
            filing_time=datetime.fromisoformat(row["Filing Date"]),
            trade_date=date.fromisoformat(row["Trade Date"]),
            value=parse_number(row["Value"]),
        )
        for row in parse_table(html, config.CLUSTER_HEADER)
    ]


def parse_trades(html: str) -> list[Trade]:
    """Parse one page of the screener, one row per trade."""
    return [
        Trade(
            ticker=row["Ticker"],
            company=row["Company Name"],
            insider=row["Insider Name"],
            title=row["Title"],
            trade_type=row["Trade Type"],
            filing_time=datetime.fromisoformat(row["Filing Date"]),
            trade_date=date.fromisoformat(row["Trade Date"]),
            price=parse_number(row["Price"]),
            qty=int(parse_number(row["Qty"])),
            value=parse_number(row["Value"]),
            flags=row["X"],
        )
        for row in parse_table(html, config.TRADES_HEADER)
    ]


def get_page(session: requests.Session, url: str, params: dict[str, str] | None = None) -> str:
    """GET a page with a timeout and bounded retries; raise FetchError when all tries fail."""
    for attempt in range(1, config.HTTP_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=config.HTTP_TIMEOUT_SECONDS)
            response.raise_for_status()
            return response.text
        except requests.RequestException as err:
            log.warning("GET %s failed (try %d of %d): %s", url, attempt, config.HTTP_RETRIES, err)
            if attempt < config.HTTP_RETRIES:
                time.sleep(config.RETRY_BACKOFF_SECONDS * attempt)
    raise FetchError(f"GET {url} failed after {config.HTTP_RETRIES} tries")


def new_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = config.USER_AGENT
    return session


def fetch_clusters(session: requests.Session) -> list[ClusterRow]:
    rows = parse_cluster_rows(get_page(session, config.CLUSTER_URL))
    if not rows:
        raise FetchError("the cluster buys page has no rows")
    log.info("cluster page: %d clusters", len(rows))
    return rows


def fetch_trades(session: requests.Session) -> list[Trade]:
    """Fetch every purchase in the window, page by page while pages come back full."""
    trades: list[Trade] = []
    for page in range(1, config.MAX_TRADE_PAGES + 1):
        time.sleep(config.SECONDS_BETWEEN_REQUESTS)
        params = {**config.SCREENER_PARAMS, "page": str(page)}
        batch = parse_trades(get_page(session, config.SCREENER_URL, params))
        trades.extend(batch)
        log.info("screener page %d: %d trades", page, len(batch))
        if len(batch) < config.TRADES_PER_PAGE:
            break
    else:
        raise FetchError(f"more than {config.MAX_TRADE_PAGES} full pages of trades; raise the cap")
    if not trades:
        raise FetchError("the screener returned no purchases at all")
    return trades
