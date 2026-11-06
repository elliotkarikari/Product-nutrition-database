# Railway deployment

Existing service: https://product-nutrition-database-production.up.railway.app
Repository: elliotkarikari/Product-nutrition-database, branch shelfscale-open.
Elliot confirms pushes auto-deploy. Do not create another service or edit main.

`railway.toml` tracks the start command, /health startup check, 60-second health timeout and bounded failure restarts. Python >=3.11 is required. Railway provides PORT and TLS. Run from repository root so snapshotted data is present. The runtime has no third-party dependencies. Railway's account-level source/build settings have not been inspected; confirm the deployment details show this config file as the source before relying on them. Reference: https://docs.railway.com/config-as-code/reference.

Before each push run `PYTHONPATH=src python3 -m unittest discover -s tests -v`.
After push compare `git rev-parse HEAD` to `git ls-remote origin refs/heads/shelfscale-open`, then check `/health` and one real lookup. A healthy old deployment is not proof that the new revision deployed.

## Phase 5 checkpoint

Before pushing required-key hardening, Elliot must set a nonempty printable-ASCII secret token (no spaces) `SHELFSCALE_API_KEY` in the existing Railway service's Variables panel and confirm it is deployed. Do not put the secret in Git, docs, chat or command output. Hardening refuses startup without it; /health and / stay public, and all assessment-producing POST routes (including lookup) require X-API-Key. Hold that push until confirmation. Current implementation status is in memory/build_memory.md.

The implemented limiter is in memory, shared across the single configured key in one process: 60 authorized POST requests in a rolling minute, with 429 and Retry-After. Bulk calls count as one request, capped at 1,000 items and 5 MB. It resets on restart and is not a distributed quota or usage-metering service. Keep one replica for that contract; scaling requires a new rate-limit design.

Before startup readiness the server verifies the source snapshots and builds the composed index. Missing/invalid keys and changed source snapshots fail startup. Railway's `RAILWAY_GIT_COMMIT_SHA`, when present and a valid SHA, is exposed as `revision` on the two public GET routes. Compare it with GitHub after deployment.

For authenticated smoke checks, make the same key available to a local process through a secure environment or ignored `.env` file. Do not echo it or put it in a command-line argument. Send it only to this existing service over HTTPS; record the response facts, never the request header. Verify `/health`, unauthenticated POST rejection, and an authenticated real lookup with overlay provenance. Avoid live quota/load tests; the deterministic local suite covers 429 behavior.

## Recovery

Use Railway's existing deployment history to roll back to a known working checkpoint. Do not rewrite branch history. Keep the key set when rolling between hardened revisions. Inspect failed deployment logs and configuration without printing secrets. If no deployed revision identifier is available, record the behavioral probes and that limit explicitly.
