# API access and request quota

Status: active
Decision maker: Elliot (required key/quota/public routes/checkpoint); Codex (mechanics within mandate). Date: 2026-11-05.

Decision: require a nonempty printable ASCII environment token without spaces before binding. Authenticate exactly one X-API-Key header in constant time on all four POST routes. Use a lock-protected rolling 60-second deque, 60 admitted authenticated requests per shared key/process; malformed authenticated requests count, unauthorized/public requests do not. Excess returns 429 and rounded-up Retry-After. Bulk counts once within existing size/item caps. Public root/health reveal no credential; expose only a validated optional Railway Git SHA. Validate source snapshots before serving.

Reasoning: one configured service key needs one bounded quota, not unbounded client-IP buckets. A rolling window avoids fixed-window bursts. Multi-replica accounting and organisation keys require a later design; document the single-process constraint rather than implying distributed limits.

Evidence: src/shelfscale/api.py; tests/test_api_hardening.py; docs/API.md and DEPLOYMENT.md. No new dependencies. Hold the auto-deploying push until Elliot confirms SHELFSCALE_API_KEY is set/deployed on the existing Railway service.
