# Security boundary

Local accounts use salted scrypt password hashes, SHA-256 session-token hashes and rotating hashed recovery codes. Tokens expire after 12 hours. Password resets revoke existing sessions. Server queries scope private strategies, reports, attachments and watches by user ID. The browser keeps tokens in session storage; logout and expired sessions clear private UI state.

Only `web/` is served publicly. `.env`, market files and the private SQLite directory are not static resources. Public Pages builds never collect account passwords. AI outputs are validated against a closed rule language and never evaluated as executable code. Document extraction has size/page limits; scanned PDF OCR is not enabled. Untrusted text is escaped in the interface, external links are limited to HTTP(S), and CSV exports neutralise formula-like strings.

The local backend includes basic in-process rate limits, bounded queues and trusted-host/CORS settings. These are not a production perimeter. Configured model/search providers receive the prompt and relevant document text; do not include material you do not want sent to that provider. Search queries are instructed to contain public method names only, but this is not a formal data-loss-prevention guarantee.

Never commit `.env`, data files, account databases, provider keys or recovery codes. Use HTTPS and stronger operational/identity controls before deploying the backend for shared public access. Dependency updates require review and re-running the suites.
