# Execution and measurement

## Daily simulation

Rules see information available through a completed close. A qualifying signal trades at the next available session open; the last close never creates a fictional later fill. A test begins in cash, including holdout runs. Earlier history warms indicators but does not create pre-existing positions at the start date.

Cash is split equally across selected stocks at inception. Sleeves are independent: no shared wallet, cash transfers or scheduled rebalancing. Each entry uses the configured percentage of that sleeve's cash, with integer whole shares. Positions are long-only, with no leverage.

Existing exit signals execute at the open before intrabar stop/target checks. Opening gaps through a stop or target fill at that open. Otherwise a bar touching both stop and target assumes stop first, since OHLC cannot reveal the sequence. A new position may stop out on its entry bar. Trailing levels update from the completed bar's high and become effective on the next bar. ATR entry levels use the prior completed ATR. Unavailable ATR blocks the entry. Paper watches keep positions open; ordinary reports liquidate remaining positions at the final close with costs.

Fees and adverse slippage apply on both entry and exit. Defaults are explicit assumptions, not verified Indian brokerage charges or historical STT/GST/stamp-duty schedules. Liquidity, market impact, circuit limits, auctions, bid/ask spreads, failed orders and partial fills are not simulated.

## Rules and data

Expressions are a closed Pydantic-validated language; no eval, generated Python, SQL or shell executes. Limits bound nesting, number of nodes, windows, stock counts and parameter search. SMA, EMA, Wilder RSI/ATR, highs/lows, ROC, standard deviation, arithmetic, crossovers, comparisons and logical groups are supported. Highest/lowest includes the current bar; lag by one for the previous range. Missing values retain an unknown state through logical operations and cannot become entries through negation.

Stock and benchmark calendars must match in the actual tested interval. Coverage truncation is disclosed. Both performance series exclude dividends. Fundamentals are joined by public availability, conservatively lagged to the next calendar day. Known survivorship and adjustment limitations remain visible in the report.

## Metrics

Return and CAGR use the starting capital and actual tested dates; CAGR uses calendar years of 365.25 days. Sharpe uses daily equity returns, sample standard deviation, 252 trading sessions and a zero risk-free rate. Drawdown is decline from the running peak. Win rate is the percentage of closed trades with positive net P&L; no-trade win rate and undefined profit factor/Sharpe are null, not invented zeros. Exposure is the average fraction of sleeves exposed during a session, not the percentage of capital invested. Excess return is percentage-point difference from Nifty 50, not risk-adjusted alpha.

## Optimisation

Up to four parameters, at most 20 candidates each and 100 evaluated combinations. Oversized grids use deterministic sampling with seed 42. Train share defaults to 70% (50–85% permitted). Candidates are scored only on earlier training data and must meet the minimum trade count. The winner is frozen before one later holdout evaluation. Holdout starts in cash with earlier history available only for indicator warm-up. The selected strategy is preserved in the audit snapshot. Repeatedly revisiting one holdout reduces its independence; this is not nested cross-validation or a complete walk-forward framework.

## Paper signals

The backend scans once per minute while running. Watches baseline at activation and process newly completed bars only. Today's daily bar is eligible at 16:00 Asia/Kolkata. Alerts are based on historical simulated holdings, not actual broker holdings. Close events are actionable at the following open; STOP_OBSERVED is retrospective daily-candle information. Events are deduplicated by watch/date/symbol/action. If multiple sessions arrived while offline, only the newest event is reported; missed alerts are not replayed. No email, webhook delivery or broker orders are implemented.
