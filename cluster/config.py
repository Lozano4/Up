"""Settings and constants for the pipeline.

Every number from the project spec in CLAUDE.md lives here, in one place.
"""

from __future__ import annotations

from pathlib import Path

# --- Paths -----------------------------------------------------------------

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = REPO_ROOT / "data"
CLUSTERS_DIR: Path = DATA_DIR / "clusters"
TRADES_DIR: Path = DATA_DIR / "trades"
REPORTS_DIR: Path = REPO_ROOT / "reports"
LATEST_REPORT: Path = REPORTS_DIR / "latest.md"

REPORT_TIMEZONE = "America/Los_Angeles"

# --- Network -----------------------------------------------------------------

HTTP_TIMEOUT_SECONDS = 30
HTTP_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2.0
SECONDS_BETWEEN_REQUESTS = 1.0
# OpenInsider is a public site; a plain browser string avoids bot blocks.
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Safari/605.1.15"

# --- OpenInsider ---------------------------------------------------------------

OPENINSIDER_BASE = "http://openinsider.com"
CLUSTER_URL = f"{OPENINSIDER_BASE}/latest-cluster-buys"
SCREENER_URL = f"{OPENINSIDER_BASE}/screener"
WINDOW_DAYS = 30
TRADES_PER_PAGE = 1000
MAX_TRADE_PAGES = 5
# Screener query: purchases only, trade date in the last WINDOW_DAYS, one row per trade.
SCREENER_PARAMS: dict[str, str] = {
    "xp": "1",
    "td": str(WINDOW_DAYS),
    "grp": "0",
    "cnt": str(TRADES_PER_PAGE),
    "sortcol": "0",
}

# Headers verified against the live pages on 2026-10-26.
CLUSTER_HEADER: tuple[str, ...] = (
    "X", "Filing Date", "Trade Date", "Ticker", "Company Name", "Industry", "Ins",
    "Trade Type", "Price", "Qty", "Owned", "ΔOwn", "Value", "1d", "1w", "1m", "6m",
)  # fmt: skip
TRADES_HEADER: tuple[str, ...] = (
    "X", "Filing Date", "Trade Date", "Ticker", "Company Name", "Insider Name", "Title",
    "Trade Type", "Price", "Qty", "Owned", "ΔOwn", "Value", "1d", "1w", "1m", "6m",
)  # fmt: skip

# --- Filter --------------------------------------------------------------------

PURCHASE_CODE = "P"  # open-market purchase
MIN_UNIQUE_INSIDERS = 2
