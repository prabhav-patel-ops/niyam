# Production preparation audit

Audit date: 29 October 2026. Base source: `865d642b3f16a09a931cb2fdc5f76981bdd00a93`. Scope: application code, data/simulation boundaries, browser user journey, account separation, resource controls, dependencies and deployment preparation. This is an engineering audit with remediation, not independent security certification or proof of profitable trading.

## Result

The application now has an operator-managed user flow: no frontend setup for backend addresses, data folders, provider keys or price-basis attestation. Once the operator supplies valid files and connection settings, users can work with the managed universe. Availability updates without a page reload; settings changed in `.env` take effect after a service restart. Strategy inputs remain available because they define the experiment.

Public deployment remains conditional on the release gate in [DEPLOYMENT.md](DEPLOYMENT.md). Real market data, paid-provider credentials, a domain and a live hosting environment were not supplied. Do not describe those checks as completed.

## Findings and remediation

| Finding | Severity | Remediation |
| --- | --- | --- |
| Frontend depended on each user's local backend and manual connections | High functional | Same-origin API, removed setup navigation/forms, remote-host autoconnection, safe readiness polling and managed-universe defaults |
| pypdf 6.21.1 had three known denial-of-service advisories | High | Pinned 6.21.2 in both dependency files; repeated dependency scan |
| Body limit trusted Content-Length, allowing oversized streamed bodies | High | ASGI perimeter counts actual bytes and rejects malformed/mismatched lengths before parsing |
| Document parsing shared service resources without execution isolation | High | Disposable extraction processes, timeout, concurrency bound, Linux CPU/address-space limits and ZIP expansion limits |
| Browser session tokens were held in JavaScript storage and a backend address was user-editable | High | Same-origin HttpOnly cookies, production Secure flag, origin checks, old storage cleared and no user-supplied API origin |
| Multiple processes could reset jobs and duplicate scanners | High | Cross-platform state-directory lock; one-process deployment and coordinated shutdown |
| In-memory authentication throttles reset on restart | Medium | Transactional SQLite throttles, hashed limiter keys, expiry cleanup and Retry-After |
| Numeric expressions could be accepted as entry/exit conditions | Medium correctness | Typed expression validation and boolean entry/exit requirements, including lagged conditions |
| Raw model responses and extraction work were not sufficiently bounded | Medium | Response-size caps, interpretation concurrency slots and bounded document extraction |
| Backend status/configuration details appeared in the user setup flow | Medium | Minimal liveness, safe readiness endpoint and redacted authenticated catalog; setup template removed from public assets |
| Browser could attest to the installed price-data basis | Medium correctness | Operator-only attestation applied server-side; browser value cannot override it |
| Manually supplied current-day bars could enter research before close | Medium correctness | Backtest and optimisation truncate at completed daily data cutoff |
| Parameter names could create unsafe HTML/object paths | Medium | Identifier validation, escaped field attributes and prototype-path rejection |
| Storage growth and user recovery needed explicit controls | Medium operations | Session/report/document/watch quotas, report deletion, alert retention, registration switch and integrity-checked backup command |
| CI did not exercise real browsers or deployment configuration | Medium verification | Browser workflow, Linux/Windows matrix, dependency scans, container smoke tests and Caddy/Compose validation added |

## Executed evidence

- Python regression suite covers existing next-open fills, gaps, fees, stop/target ambiguity, future-data isolation, fundamental timing, holdout isolation and account ownership, plus the added production checks.
- DOM checks cover remote same-origin startup, preview boundaries, absence of setup tasks, managed data appearing without reload, template defaults, Hindi/Unicode labels, escaping, cookie credentials and private-state cleanup.
- A real Chrome browser completed cookie signup, a real HTTP call to a controlled model fixture, backtesting, CSV download, paper-watch creation, parameter optimisation, session restoration and logout. A 390 by 844 phone viewport was inspected and checked for horizontal overflow. Desktop and phone screenshots were visually reviewed.
- Browser data and the provider are explicitly synthetic test fixtures. Their returns are not investment results, and their model output is not evidence of a paid model's language accuracy.
- The dependency scan found three pypdf advisories in 6.21.1: `GHSA-6c7f-9265-g8fw`, `GHSA-jr96-gvgh-j3r4`, and `GHSA-gmh7-3g9r-mjh5`. After upgrading to 6.21.2, the pinned runtime requirements scan reported no known vulnerabilities. npm reported no known vulnerabilities. This is a dated database lookup, not a guarantee against unknown vulnerabilities.

Local verification: 49 Python tests and 92 DOM checks passed; the complete real-browser flow passed. CI results are recorded in the pull request. This workstation had no Docker executable, so local Docker/Caddy runtime execution is not claimed; the new container CI job must pass before deployment approval. The runtime base image and Caddy image also need the operator's normal image-patching process.

## Remaining launch checks

1. Run branch CI, including container smoke and proxy configuration checks, and inspect failures.
2. Install real vendor files. Verify price adjustments, benchmark identity, dates, missing sessions, corporate actions, delisted securities and point-in-time fundamental vintages. Reconcile representative trades and costs independently.
3. Configure the actual provider; run preflight and a labelled Hindi/English/Hinglish acceptance set. No measured interpretation accuracy percentage is established by this audit.
4. Deploy one process behind HTTPS on the target host; confirm proxy identity, secure cookies, mobile access and private persistent storage.
5. Restore a backup and run representative concurrency/dataset capacity tests. Monitor resource saturation and failed jobs; size the service accordingly.

No broker integration, live exchange certification, intraday fill accuracy, cloud provisioning, email identity verification, email recovery or horizontal scalability has been added. These are product/deployment boundaries, not hidden implemented features.
