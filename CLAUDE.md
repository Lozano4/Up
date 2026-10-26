# insider-cluster

A private Python project that finds insider cluster buys: companies where two or more different insiders bought their own company's stock on the open market within the last 30 days. It runs on GitHub Actions every weekday and writes a ranked Markdown report to `reports/`. It NEVER places trades, never talks to a broker, never stores broker credentials. It only reads public data and writes files in this repo.

## Project spec

PURPOSE
Phase 1: pull OpenInsider's latest cluster buys, confirm each one against the individual Form 4 trades, keep only real open-market purchase clusters, and write a ranked report. A human reads the report and makes every decision. Phase 2 (not started, do not build yet): Alpaca.

DATA SOURCES
A. Cluster list: GET http://openinsider.com/latest-cluster-buys. One row per cluster in the table with class "tinytable". Header, verified 2026-10-26: X, Filing Date, Trade Date, Ticker, Company Name, Industry, Ins, Trade Type, Price, Qty, Owned, ΔOwn, Value, 1d, 1w, 1m, 6m. Saved as data/clusters/YYYY-MM-DD.csv.

B. Individual trades: GET http://openinsider.com/screener with xp=1 (purchases), td=30 (trade date in the last 30 days), grp=0 (one row per trade, not grouped), cnt=1000, page=N. Header, verified 2026-10-26: X, Filing Date, Trade Date, Ticker, Company Name, Insider Name, Title, Trade Type, Price, Qty, Owned, ΔOwn, Value, 1d, 1w, 1m, 6m. Fetch the next page only while a page comes back full, up to 5 pages. Saved as data/trades/YYYY-MM-DD.csv.

Both: send a browser User-Agent, 30-second timeout, 3 tries, 1 second between requests. Fail loudly if the table is missing or the header does not match.

FILTER
A cluster from A is kept when, among the trades from B for that ticker:
- the trade code is P (the "P - Purchase" in Trade Type; open-market buy, not an award, option exercise or gift),
- the trade date is within the 30 calendar days ending on the report date (Pacific), inclusive,
- and at least 2 unique insiders made such trades (names compared case-insensitively with spaces collapsed).
Tickers on the cluster page that fail are listed in the report with the reason.

RANKING
Unique insiders, most first; then total dollar value of the qualifying purchases, largest first; then ticker A to Z.

REPORT
reports/YYYY-MM-DD.md (Pacific date) and reports/latest.md, identical. Header line with the date, generated time (Pacific), and the trade-date window. A summary count. A ranked table: rank, ticker (linked to its OpenInsider page), company, insiders, buys, total value, first trade, last trade, latest filing. Then one short section per kept ticker listing each buy (insider, title, trade date, price, quantity, value). Then the dropped tickers with their reasons. Nothing is written until both fetches have succeeded.

SCHEDULE
Weekdays at 13:00 UTC (6:00 AM Pacific in summer, 5:00 AM in winter), after the previous day's filings are in. The job commits data/ and reports/ back to main. No secrets are needed.

NEVER
Place orders, connect to Alpaca or any broker, store broker credentials, or write a report built from a failed fetch.

## Working rules

- Python 3.11 or newer.
- Type hints everywhere.
- Dataclasses for structured data; no loose dicts passed between modules.
- pathlib for all filesystem paths.
- logging, never print.
- Specific exceptions only; no bare `except:` and no `except Exception` without re-raising.
- Format with black, lint with ruff; both must pass before a commit.
- Functions under about 40 lines. Split when they grow.
- No secrets in code. If one is ever needed, read it from the environment or a `.env` file; `.env` is gitignored.
- Every external call has an explicit timeout and bounded retries.
- Every job must fail loudly: non-zero exit and a clear log line. Never write a stale or partial report on top of a failed fetch.
- Layout: `cluster/` is the package, `data/` holds fetched inputs, `reports/` holds the Markdown reports, `tests/` holds pytest tests.
- Run locally with `.venv/bin/python -m cluster <command>`; commands are `fetch`, `report`, `run-all`.
