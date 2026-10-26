# insider-cluster

A private, read-only Python pipeline that finds insider cluster buys. It pulls OpenInsider's latest cluster buys, checks each one against the individual Form 4 trades, keeps only companies where 2 or more different insiders made open-market purchases (code P) in the last 30 days, and writes a ranked Markdown report to `reports/`. It runs on GitHub Actions every weekday. It never places orders, never connects to Alpaca or any broker, and never writes a report built from a failed fetch. To run locally: `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`, then `.venv/bin/python -m cluster run-all` (or `fetch`, then `report`), and `.venv/bin/pytest` to run the tests.

## How it runs

GitHub Actions runs `.github/workflows/report.yml` on weekdays at **6:00 AM Pacific** (13:00 UTC; 5:00 AM during standard time). It runs the tests, fetches both OpenInsider pages, writes the report, and commits `data/` and `reports/` back to `main` with a message like `report 2026-10-26`, so the repo history is the data history.

**Where the report lives.** `reports/latest.md` is today's report (GitHub shows it formatted). Dated copies sit next to it. The raw inputs are under `data/clusters/` (OpenInsider's cluster page) and `data/trades/` (every open-market purchase in the window).

**Running it by hand.** Open the Actions tab, pick the `report` workflow, click "Run workflow" on `main`. The run's summary page shows the whole report.

**If a run is red.** Open the failed run, click the red step, and read the first red line. "unexpected table header" means OpenInsider changed its page layout; a "failed after 3 tries" line means the site was down. Nothing is committed from a failed run, so `latest.md` keeps the last good report.

**No secrets** are needed.
