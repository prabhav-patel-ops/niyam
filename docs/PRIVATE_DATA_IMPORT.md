# Private historical data and Yahoo enrichment

Niyam can preserve the supplied AlgoAnalytics collection privately and use validated Yahoo daily bars in its existing backtesting engine. This is an operator task. Users do not upload data or enter API credentials in the frontend.

## What is imported

`scripts/import_dataset.py` imports the 28 named source files defined in `app/private_import.py`. It copies every original into a new private generation, verifies SHA-256 checksums, and writes a DuckDB warehouse and manifest. The source directory is never changed. CSV values, company mappings, the sector workbook and metric reference are treated as data; embedded text and formulas are never executed.

The warehouse separates closes, indices, period financial values, monetary turnover, company mappings, sectors, reference text and non-numeric values. Every financial observation retains its source file, row, column, reporting basis and unit. Zero is preserved as zero. Consolidated and standalone values remain separate. Company-name matches are candidates for review, rather than verified identities. Current sector classifications are not treated as historical classifications.

Period labels such as March 2024 are financial periods. They are **never publication dates**. `available_at` remains null until independently verified. These observations are staged, not silently activated as historical trading signals.

## Run the import

Run from the repository root with the backend virtual environment active. Substitute your private source directory:

```powershell
python -m pip install -r requirements.txt -r requirements-data.txt
python scripts/import_dataset.py --source-dir "E:/AlgoAnalytics/VM/data" --data-dir data --adjustment-basis split_bonus_adjusted_ex_dividend
python scripts/fetch_yahoo.py --source-dir "E:/AlgoAnalytics/VM/data" --data-dir data
python scripts/install_market_data.py --data-dir data
```

Confirm the price basis privately in `.env`:

```dotenv
NIYAM_PRICE_BASIS=split_bonus_adjusted_ex_dividend
```

Only confirm this after checking the supplier's corporate-action treatment. `--data-dir` must match the service's `NIYAM_DATA_DIR`, or use the default repository `data` directory for both. Run imports while the service is stopped, then restart it after installation. The publisher replaces the equity and benchmark files individually; it is not a live multi-file database transaction.

## Yahoo daily prices

The downloader requests daily open, high, low, close, share volume and corporate actions. It explicitly disables `auto_adjust` and `back_adjust`, excludes `Adj Close`, and retains dividends/splits separately as evidence. This supports the engine's dividend-excluding price-return model; it does not calculate total returns. Supplied monetary turnover is never converted into share volume.

The downloader excludes the current incomplete Indian-market day. Missing required values are recorded as removed rows; inconsistent OHLC values reject that stock's download. It does not repair bars, invent sessions or substitute close for open. Delisted, renamed and unsupported tickers can fail. Requests are paced, and a rate-limit response stops new work. Results and failures are checkpointed privately, so the command can resume. Use `--retry-failed` for an explicit retry, or `--symbols RELIANCE.NS,TCS.NS` for a subset. Failed downloads are not counted as usable histories.

The installer validates cached rows again and installs one equity Parquet file. Histories with fewer than three observations are excluded from the available-stock catalog. It retains the supplied Nifty 50 price-index history and adds missing Yahoo index dates only after overlap reconciliation passes. It records missing equity sessions and stock sessions absent from the benchmark. Complete histories appear first in the default stock list. A stock with gaps may still work over a shorter complete period; the engine checks the exact requested dates and refuses gaps. It never forward-fills missing prices. Some special trading sessions are missing from Yahoo and require another source.

The private installation report contains the failed-symbol list, coverage gaps, benchmark comparison and dataset fingerprint. The managed catalog makes page refreshes inexpensive, while strategy runs read only their selected stocks from Parquet. The fingerprint still identifies the full canonical dataset. Private imports and provider caches are ignored by Git and are not deployed by publishing code to GitHub.

## Earnings dates do not finish the financial import

An optional evidence scan is available:

```powershell
python scripts/fetch_earnings.py --source-dir "E:/AlgoAnalytics/VM/data" --data-dir data
```

Yahoo earnings calendars can include estimates and future dates, and do not identify the fiscal period or every metric released in a particular announcement. The script preserves provider timestamps and flags future events; all rows are marked unusable for point-in-time joins. Its checkpoints are resumable. A partial evidence scan is not a completed publication-date dataset. Do not join the nearest earnings date to a financial period or assume all financial metrics were published together.

To activate fundamental rules, an operator must supply verified symbol/period identities, publication timestamps, units, reporting basis and historical versions. Resolve conflicting observations first, then create the canonical `symbol,available_at,...` table described in [DATA.md](DATA.md). The rule language supports ROE, ROCE, PE, PB, PS, book value per share, EPS, FCF, revenue, shares outstanding, capital employed, CFO, capex, PBT, interest expense and market cap. Support for a field does not mean verified data exists for that field. No valuation ratios are inferred from uncertain units or mismatched dates.

## What is still required for launch

- Repair failed or incomplete OHLCV histories with a suitable historical source; review ticker changes, delistings and corporate actions. Present-day ticker lists alone cannot eliminate survivorship bias.
- Verify publication dates and historical financial versions; review ambiguous mappings, units and statement basis. Current sector information cannot reconstruct historical membership.
- Confirm data-use rights for the intended audience. Yahoo access is not itself a redistribution license; review the provider's terms before commercial or public use. See the [yfinance project notice](https://github.com/ranaroussi/yfinance).
- Set backend model credentials, deploy the Python backend on a persistent server, and complete the checks in [DEPLOYMENT.md](DEPLOYMENT.md). GitHub Pages serves the preview frontend and cannot run this Python engine or store private financial data.

Successful schema checks and sample backtests demonstrate functioning ingestion and execution. They do not establish vendor accuracy, future strategy profitability or production readiness for every stock/date range.
