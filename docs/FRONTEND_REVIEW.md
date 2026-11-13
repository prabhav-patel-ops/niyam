# Phone frontend review

The GitHub Pages build is an interactive, backend-free review of Niyam's latest interface. It does not require sign-in, a computer running Niyam, API keys, or a shared Wi-Fi network.

Use the navigation menu to explore the strategy studio, saved strategies, sample backtests, tax comparison, parameter-search layout, daily signals and paper portfolios. The toolbox supports search, category filters, clickable references and `@` suggestions. Fundamental fields remain visible with their pending requirements.

Every screen is labelled **Frontend review · sample data**. Results, coverage, trades, taxes, optimiser selections and paper holdings are synthetic interface fixtures. They do not evaluate edited rules or represent actual market data. Free-form prompts are not interpreted by AI. Formula validation and document processing require the connected backend and remain unavailable here. No file is uploaded.

Edits and sample additions are held in memory and reset when the page reloads. Do not use this public preview for private strategy research or actual trading. Private datasets, account state, `.env` files and provider keys are not part of the build.

Build with `python scripts/build_pages.py --output /path/outside/repo`. The generated folder can be hosted by any static web server, or opened through its `index.html`. Verify with `node tests/review.cjs`; this checks the review flows and asserts zero backend requests.

The normal local backend build keeps review mode disabled. Only the Pages build enables `NIYAM_PUBLIC_PREVIEW` and `NIYAM_REVIEW_MODE` together.
