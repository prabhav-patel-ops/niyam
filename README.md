# Niyam

Describe a daily Indian-stock strategy in Hindi, English or Hinglish, review its exact rules, backtest against the Nifty 50 price index, and follow daily paper signals.

## User experience

Users open the hosted workspace, create an account, choose a template or describe an idea, review the rules, and run research. They are not asked to supply a backend address, market files or provider keys. The browser uses the same server that serves the page. Data and API connections belong to the operator.

The app periodically discovers backend readiness and available stocks. Data-file updates are picked up automatically when files change; provider/environment changes require a backend restart. If research is not ready, users see a temporary service message, never setup forms or invented results. User choices such as strategy, dates, stocks and cost assumptions remain editable.

GitHub Pages is a static product preview only. It does not collect passwords, run Python or provide a hosted trading service. A working workspace requires deploying the backend and frontend together.

## Operator setup

1. Install Python 3.12 and extract the repository.
2. Copy `.env.example` to a private `.env` and configure the model connection.
3. Put daily prices in `data/prices/` and Nifty 50 price-index data in `data/benchmark/`. Optional point-in-time fundamentals belong in `data/fundamentals/`.
4. Verify split/bonus adjustment and dividend exclusion, then set `NIYAM_PRICE_BASIS=split_bonus_adjusted_ex_dividend` in `.env`.
5. Run `python scripts/start.py` (Windows: `py -3.12 scripts/start.py`) and open `http://127.0.0.1:8000` for local development.
6. Run `.venv/bin/python scripts/preflight.py --probe-model` before a real-data launch. Windows uses `.venv/Scripts/python.exe`.

Market data, keys and accounts ship empty. They are excluded from version control. Never place private data inside `web/`.

For an HTTPS deployment, use the [operator runbook](docs/DEPLOYMENT.md). The supported architecture is one backend process with persistent local SQLite storage behind a trusted TLS proxy. It is not a horizontally scaled service. The [audit record](docs/PRODUCTION_AUDIT.md) distinguishes verified code behaviour from outstanding deployment and real-provider checks.

## Features

- Editable SMA, RSI and Donchian templates; structured rule editor; document attachments for text PDFs, DOCX, TXT and Markdown.
- Configurable multilingual interpretation with schema validation, bounded repair, focused clarification and optional sourced reference lookup. No generated code execution.
- Daily, long-only cash equities, up to 100 stocks, independent equal initial capital sleeves, whole shares, nested rules, lagged indicators and historical fundamentals.
- Next-open execution; fixed/trailing percentage or ATR stops; percentage targets; fees and adverse slippage on both sides.
- Return, CAGR, drawdown, volatility, Sharpe, win rate, trade ledger, monthly comparisons, CSV trades and JSON reports.
- Bounded parameter search, training-only selection and a later holdout test.
- Private account resources, HttpOnly browser sessions, hashed credentials and rotating recovery codes.
- Optional backend feed and daily paper watches with duplicate-event protection. No broker orders, intraday alerts, email or webhooks.

## Verification

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
npm ci --ignore-scripts
npm test
npx playwright install --with-deps chromium
npm run test:browser
```

Browser tests start an isolated synthetic fixture with a test model endpoint. They do not contact a paid provider or represent investment performance. Set `NIYAM_TEST_PYTHON` if Python is outside `.venv/` (for example `python` in CI).

CI runs Python tests on Linux and Windows, DOM checks, Linux Chromium flows, dependency scans, container smoke tests, backup restoration, and a production HTTPS proxy/backtest/session flow. See the current CI result before treating a release as passed.

[Data contract](docs/DATA.md) · [Simulation method](docs/METHOD.md) · [Audit](docs/PRODUCTION_AUDIT.md) · [Security](SECURITY.md) · [Research](docs/RESEARCH.md)

Unsupported: intraday trading, shorts, derivatives, leverage, cross-stock ranking and portfolio rebalancing. No interpretation or trading accuracy percentage is established. Review interpreted rules and validate the actual dataset and provider before relying on research.
