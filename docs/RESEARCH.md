# Research and reuse

The interface takes the natural-language-to-reviewed-rules workflow used by products such as Composer, while keeping the calculation engine deterministic and the data local. We reuse trained models through provider APIs instead of training a model from scratch. No provider weights or paid credentials are bundled.

- [Composer Create with AI](https://help.composer.trade/article/108-create-with-ai): reference for explaining intent and inserting a review step before backtesting.
- [TradingView strategy execution documentation](https://www.tradingview.com/pine-script-docs/concepts/strategies/): reference for daily execution, broker-emulator assumptions and ambiguous intrabar sequences.
- [LEAN](https://www.quantconnect.com/docs/v2/lean-engine/getting-started): a broader established event engine, useful if future scope expands into a much larger trading platform. Not embedded here.
- [vectorbt](https://github.com/polakowo/vectorbt): vectorised research reference; its [license](https://github.com/polakowo/vectorbt/blob/master/LICENSE.md) includes Commons Clause restrictions. Not embedded.
- [Backtesting.py](https://kernc.github.io/backtesting.py/): independent development-only comparison oracle. Its AGPL license remains applicable; it is not a runtime dependency.
- [DuckDB](https://duckdb.org/docs/stable/data/parquet/overview): reused for canonical CSV/Parquet ingestion.
- [Numba](https://numba.readthedocs.io/en/stable/user/jit.html): reused to compile the simulation loop to native code. A separate C++ implementation is not presently necessary for the measured daily workload.
- [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B): a possible openly available multilingual model for a later local inference evaluation. Not installed or benchmarked here; Hindi accuracy is not assumed from model metadata alone.
- [Tavily search API](https://docs.tavily.com/documentation/api-reference/endpoint/search): optional bounded named-method lookup. Documents and search excerpts are treated as untrusted strategy content.
- [GitHub Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits): basis for the static public preview / local account boundary.
- [OpenAI billing](https://help.openai.com/en/articles/9039756-managing-billing-for-chatgpt-and-the-api-platform): ordinary subscription/API billing separation. ChatGPT-specific OAuth integration is not implemented by this app.

Model/provider testing should include Hindi, Hinglish, typos, adversarial document instructions, indicator lookback ambiguity, unsupported features and minimal clarification. A universal promise to understand every strategy without asking questions would be inaccurate.
