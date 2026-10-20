# Release audit

Verified on the source published in this repository; the real market dataset and provider credentials are intentionally absent.

## Executed checks

- **33 Python tests passed.** Next-open timing, opening gap fills, stop/target ambiguity, trailing-stop causality, costs, no fictional final signal fill, accounting reconciliation, unavailable indicators under NOT, missing stock/benchmark dates, future-data perturbation, point-in-time fundamentals, train/holdout isolation, private API access, account hashing/recovery, attachment access, real job completion, feed merge/closed-bar handling and redacted feed failures.
- One SMA execution case agrees with an independent Backtesting.py oracle under matching assumptions. This is not proof that every strategy agrees with every platform.
- **49 jsdom DOM checks passed.** Navigation, editable templates, public-preview sign-in boundary, local signup/recovery, missing-model state, clarification retry, output escaping, CSV formula protection and expired-session cleanup.
- JavaScript syntax and Python compilation pass. Public build includes only web assets. Data directories contain only empty Git placeholders. Connection values remain blank.
- Synthetic performance measured in `BENCHMARK.json`: 3,200 bars per stock; warmed median **27.72 ms** for one stock, **331.13 ms** for 50-stock full reports, and **2,889.46 ms** for 40 trials across 10 stocks with winner reports. First call **1,702.10 ms**. These figures exclude disk ingestion, AI, API/queue/network and browser latency. They are not a service guarantee.

## Verification limits

No cloud browser was available, so visual/mobile/browser-network behavior has not been audited. jsdom does not verify layout, mixed-content restrictions or real browser permissions. The flowchart is a native SVG/HTML document.

No real provider calls, model accuracy evaluation, user market-data validation, broker integration, live exchange feed, AWS deployment, Windows launcher run or Docker runtime test has been performed. The generic feed and model adapter have controlled tests, not vendor certification.

The data reader loads canonical data into memory and is not yet a vendor-specific large-data parser. Public Pages is a preview; local registration is functional, but the laptop service is not a globally hosted multi-user backend. See METHOD, DATA and SECURITY for execution and operational limits.

Earlier session-only artifacts were unavailable when publication resumed. The restored source was rechecked; this audit supersedes earlier attachment-specific test counts and timings.
