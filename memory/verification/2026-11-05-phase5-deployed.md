# Phase 5 deployment verification

Verifier: Codex. Recorded: 2026-11-05T23:28:59.079494-05:00.

Elliot confirmed the Railway variable was set in this chat. Sync fetched origin: local 994d2c1a1a1cc39c0f699af1469d7a3dd516aba4 was the two expected held commits ahead of 9316caaf; no divergence. Existing untracked .DS_Store preserved. Local .env remains ignored and untracked; its token was read only into the HTTPS request header, never printed or committed.

PASS before push: PYTHONPATH=src python3 -m unittest discover -s tests -v — 131 tests in 7.798s; Final record-only pre-push rerun: 131 tests in 7.799s; that latest log is alongside this record. git diff --check passed. git push origin shelfscale-open succeeded and git ls-remote confirmed 994d2c1a1a1cc39c0f699af1469d7a3dd516aba4.

PASS live: the first health probe still served the older revision; after waiting for rollout, /health and / returned HTTP 200 and revision 994d2c1a1a1cc39c0f699af1469d7a3dd516aba4. POST /v1/lookup without a key returned 401; the same route with the locally saved key returned 200 for beef 18-017. Energy 523 kJ carries uk-beef-2024 provenance and the superseded CoFID observation ID. Root advertises the shared 60-request quota. Full sanitized response evidence is alongside this record. This confirms the deployed key matches the local key without exposing either.

Limits: rate-limit/concurrency behavior tested locally, not load-tested live. Railway account settings remain uninspected. 2018 beef score remains honestly unavailable without AOAC fibre. The final record-only commit changes no runtime code; resolve its head with git log -1 --format=%H -- memory/build_memory.md. Historical held-state records are retained, superseded as current state by this deployment event.
