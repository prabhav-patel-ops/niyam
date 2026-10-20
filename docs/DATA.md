# Data contract

All paths are relative to the extracted project. `NIYAM_DATA_DIR` can override the root locally. Files stay private and are excluded from Git. Send a small representative sample before asking for a vendor-specific adapter; this initial parser intentionally accepts a canonical schema.

## Prices: `data/prices/`

CSV or Parquet, with columns:

```text
date,symbol,open,high,low,close,volume
```

Use ISO dates `YYYY-MM-DD`, one unique symbol/date row, finite positive OHLC, nonnegative volume and consistent highs/lows. Symbols are normalized to uppercase. All stocks must cover every Nifty 50 session in the tested interval; extra stock sessions with no benchmark row also fail clearly. No automatic forward-filling of prices or invented fills. Multiple files may partition dates or stocks but must not overlap.

Use OHLC consistently adjusted for splits and bonuses, **excluding dividends**. Corporate actions are not computed automatically. Supply volume in a consistent basis and document it. Price adjustments can change whole-share sizing and transaction-cost estimates; review raw-share execution requirements before treating results as brokerage-accurate. The user must confirm the price basis explicitly.

## Benchmark: `data/benchmark/`

CSV or Parquet with `date,close`. Optional `symbol` must be `NIFTY50` or `NIFTY 50`. Supply the **price index**, not the total-return index (TRI), because the engine excludes dividends. The reader can reject an explicitly mismatched label; it cannot establish the true provenance of an unlabeled series. Historical index membership is not inferred.

## Fundamentals: `data/fundamentals/`

```text
symbol,available_at,roe,roce,pe,pb,ps
```

`available_at` is when the information was public, not the financial period end. ISO timestamps can include an offset. Date-only releases become usable on the following calendar day in Asia/Kolkata. Fields join backward as of each price date, never from the future. Consolidate multiple releases becoming available on the same date. ROE and ROCE use percentage points (15 means 15%); valuation ratios use multiples. Unknown values cannot trigger rules, including through NOT. Restated and revised fundamentals require point-in-time vintages from the provider.

## Optional daily feed

Set `DAILY_FEED_URL` in the local `.env` to an operator-controlled HTTPS endpoint. `DAILY_FEED_API_KEY`, if set, is sent as a Bearer header. Local loopback HTTP is allowed for development. The backend requests JSON at most once every five minutes while running:

```json
{
  "prices": [{"date":"2026-01-02","symbol":"EXAMPLE","open":100,"high":102,"low":99,"close":101,"volume":1000}],
  "benchmark": [{"date":"2026-01-02","close":25000}]
}
```

Those numbers are illustrative schema examples, not market data. Responses are bounded to 10 MB and 30 seconds. Future rows and today's bar before 16:00 IST are ignored. Daily bars are upserted into `_daily_feed.csv`; explicit historical files take precedence on overlap. Do not create your own file with that reserved name. Fundamentals arrive through your files. The feed adapter is generic; no exchange/vendor subscription or broker connection is included.

## Reliability limits

The file catalog caches based on path, size and modification time; on a change it validates the dataset and computes a content fingerprint. Do not deliberately preserve both size and modification time when replacing a file. The full canonical dataset is held in RAM. File updates should be atomic. User data must be checked for corporate actions, survivorship bias, delistings, suspended sessions and trading calendars before research results are relied upon.
