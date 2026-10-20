# Deployment

## Public repository and GitHub Pages

The workflow `.github/workflows/pages.yml` copies only `web/` through `scripts/build_pages.py` and enables public-preview mode. Choose **Settings → Pages → Build and deployment → Source → GitHub Actions**. A successful run publishes https://whood-yop.github.io/niyam/ with the flowchart at `/niyam/flowchart.html`.

Pages is static hosting. It cannot run the Python backend or keep private account state. The public build deliberately sends users to their own backend workspace for registration/sign-in; passwords are not collected by Pages. Repository source is public, market data and `.env` are not. This is an open-source preview, not a commercial SaaS deployed on Pages.

## Local service

Use Python 3.12 and `python scripts/start.py`. The service binds `127.0.0.1:8000` by default. The database lives in `var/niyam.sqlite3`; back up `var/` and your data privately. Public registration is available on the backend, but a loopback server is reachable only on that computer. Save the one-time recovery code; email verification and email recovery are not installed.

Docker files are included for future deployment, but have not been runtime-tested in this environment. Compose maps only loopback, mounts `data/`, and keeps state in a named volume. Do not delete that volume if it contains accounts.

## Connections

Copy `.env.example` to `.env`; fill the provider/base URL/model and optional key. The interpreter supports an OpenAI-compatible `/chat/completions` endpoint with JSON-object responses. Provider compatibility, model quality and availability must be tested with the chosen model. Keys stay server-side. Ordinary ChatGPT Plus billing and API-platform billing are separate; this build does not implement ChatGPT OAuth/token-sharing integration. The user deliberately supplies connections later.

## AWS migration boundary

The API/worker separation and container make migration possible, but this edition is not a production multi-tenant service. Before shared internet exposure: provision HTTPS, persistent private storage and backups, a production identity system, explicit allowed origins/hosts, distributed job scheduling, API/body-size limits at the proxy, quota enforcement and per-user access tests. Replace local SQLite and in-memory queue/rate controls as load requires. Multi-worker use needs coordinated scheduling; running multiple signal scanners is not the recommended local configuration. No AWS infrastructure or credentials have been provisioned.
