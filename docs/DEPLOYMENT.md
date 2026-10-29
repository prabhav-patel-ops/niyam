# Operator deployment runbook

## Supported architecture

GitHub stores the source and runs the automated checks. GitHub Pages serves the static preview; it cannot keep the Python API, account database or job workers running. GitHub Actions is also an ephemeral test runner, not the live application host. Keep the repository on GitHub and deploy the working workspace to a server/container host under one HTTPS origin. No user-facing backend URL or credentials form is needed.

Serve `web/` and `/api/` from the same HTTPS origin. The included production Compose configuration runs one Niyam process behind Caddy, with persistent account and proxy volumes and a privately mounted market-data directory. A second process using the same state directory is refused, protecting the signal scanner and restart recovery.

This deployment is intended for a bounded initial service. SQLite, the in-process job executor and scanner are deliberate single-instance constraints. Do not add replicas or Uvicorn workers; coordinated jobs and a shared database require a separate architecture change. The container has two CPUs, a 2 GiB memory limit and 128 process/thread slots; load-test the intended dataset and user traffic before choosing these as production capacity.

## Private inputs

Copy `.env.example` to `.env` on the server. Supply:

| Setting | Meaning |
| --- | --- |
| `NIYAM_ENV=production` | Require a valid HTTPS public origin and secure cookies |
| `NIYAM_PUBLIC_URL` | Public origin such as `https://research.example.com`, with no path |
| `NIYAM_DOMAIN` | DNS hostname matching that origin |
| `NIYAM_PRICE_BASIS` | Set to `split_bonus_adjusted_ex_dividend` only after checking the source data |
| `LLM_BASE_URL`, `LLM_MODEL` | Compatible model endpoint and model identifier |
| `LLM_PROVIDER`, `LLM_API_KEY` | Operator label and provider credentials, where required |
| `TAVILY_API_KEY` | Optional reference lookup |
| `DAILY_FEED_URL`, `DAILY_FEED_API_KEY` | Optional canonical daily feed |
| `NIYAM_REGISTRATION_OPEN` | `true` or `false`; close registration when desired |

Set DNS to the server and permit inbound TCP 80/443. Keep the backend port private. If the configured `172.30.0.0/24` Docker network conflicts with the host, change its subnet, static proxy/backend addresses and trusted-proxy argument together.

Prices and benchmark use the [data contract](DATA.md). The three directories are intentionally empty in Git. Install files atomically. File changes are discovered automatically; do not preserve both modification time and size when replacing a dataset. Environment/key changes require restarting the service. `configured` or readiness booleans indicate settings and data availability, not proof of provider correctness or exchange provenance.

## Build and check

```sh
docker compose -f compose.production.yaml config --quiet
docker compose -f compose.production.yaml build
docker compose -f compose.production.yaml run --rm niyam python scripts/preflight.py --probe-model
docker compose -f compose.production.yaml up -d
```

The model probe makes one provider request using a public SMA template and can incur its normal API charge. It does not send account documents or validate all languages. Run broader interpretation acceptance tests against the chosen model separately.

The bind-mounted `data/` directory must be readable and, if the feed is enabled, writable by container UID 10001. Account state is in the `niyam-state` volume. The container filesystem is otherwise read-only; Numba cache and document processes use bounded temporary storage. Do not delete the state volume during upgrades.

Open the public URL from a desktop and a phone. Verify account creation, recovery-code storage, a reviewed real-data backtest, optimisation, CSV/JSON exports, paper-watch creation and logout. Confirm that no data/API setup form appears. Check that unauthenticated requests cannot read saved work. GitHub Pages is not a substitute for this deployment.

## Monitoring and recovery

- `/api/health` is process liveness. `/api/ready` returns 503 until research data, price-basis attestation and model settings exist. It does not make paid-provider calls.
- `/api/runtime` supplies safe readiness flags for the frontend. The browser refreshes them every 30 seconds. No provider URL, API key, filesystem path or ingestion error is included.
- Record proxy/application logs privately and alert on repeated 5xx responses, failed jobs, disk pressure, exhausted storage quotas and feed failures. Add edge-level abuse controls appropriate to traffic; application throttles are not a network flood defence.
- Browser sessions expire after 12 hours. Mailbox verification and email recovery are not implemented. Users must retain their recovery code. Registration is capped at 1,000 accounts; each account has 200 strategies, 200 reports, 50 documents with 1,000,000 extracted characters total, and 20 watches. The scanner retains the latest 1,000 alerts per account.
- A restart marks unfinished jobs interrupted. Normal shutdown requests cancellation and drains active jobs. Jobs check cancellation between safe engine checkpoints. A forced kill or host failure requires rerunning unfinished research.

Create a consistent private backup:

```sh
docker compose -f compose.production.yaml exec niyam python scripts/backup.py --output /app/var/backups/backup-YYYY-MM-DD.sqlite3
```

The command refuses an existing destination, uses SQLite's backup API, and checks database integrity. Copy backups to private storage outside the server and choose a retention schedule. Back up the installed data files and configuration separately.

Restore into a **new** private directory, never over live state:

```sh
python scripts/restore.py --input /private/backups/backup.sqlite3 --state-dir /private/niyam-restored
```

The restore command verifies database integrity and the expected schema, preserves accounts/saved work, revokes backed-up sessions, and marks unfinished jobs interrupted. Existing directories are refused. Stop the old service, preserve its state volume, configure `NIYAM_STATE_DIR` or mount a new volume containing the restored directory, preserve container UID 10001 ownership, and start only one process. Sign in again and confirm saved reports. Never replace a live WAL database by copying a single file over it.

CI exercises backup restoration through the application login and saved-strategy/report APIs. It also starts the production Compose topology with an isolated test CA, verifies HTTPS certificate trust, Secure cookie sessions, cross-origin rejection, a real template backtest through the proxy, and 32 parallel liveness reads with concurrency 8. The internal test certificate is confined to `tests/Caddyfile.smoke`; production retains public automatic HTTPS. These are synthetic integration checks, not capacity certification for an unknown real dataset or internet traffic.

## Release gate

Before public launch, require passing branch CI, container/proxy startup on the target host, successful real-provider and data preflight, inspected real-data accounting, an HTTPS/session test, a restored backup, and a representative capacity test. No live host or provider credentials are provisioned by this repository. Record that evidence with the deployed commit and dataset fingerprint.

Configuration references: [Caddy request limits](https://caddyserver.com/docs/caddyfile/directives/request_body), [Caddy reverse proxy](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy), [Uvicorn settings](https://uvicorn.dev/settings/).
