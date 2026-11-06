# Matching assistant: retrieval proposes, Jev gates, a person confirms

Status: active

Decision date: 2026-11-06

Decision maker: Elliot Karikari (engine: Jev, TypeSafe; rules); implementing agent (mechanics, thresholds pending measurement).

Decision: src/shelfscale/matching.py proposes CoFID identities for a product name and never scores. Deterministic retrieval (shared words, weighted to CoFID's head word) gives up to 6 candidates. When TYPESAFE_API_KEY is set, Jev answers one yes/no question per candidate as a probability; at or above `propose_at` a candidate is "proposed", below `abstain_below` "unlikely", between "possible". Without the key or on any Jev failure, the response says so and lists candidates as "possible" only. Nothing is scored until a user confirms; the confirmation's basis names the engine, Jev's versioned model and the probability ("model-proposed, user-confirmed") or "user-selected from deterministic candidates". Confirmations live in the visitor's browser; the service appends them to a file only when SHELFSCALE_CONFIRMATIONS_PATH names durable storage (Railway has none configured). No builder agent sits in the request path.

Wire format confirmed 2026-11-06 from the published adapter source (@tanstack/ai-typesafe 1.0.0): POST https://api.typesafe.ai/v1/systemone, Authorization: Bearer <key>, body {model, state, questions}; noul answers {"type":"noul","noul":p}; reply names the versioned model. The key variable is TYPESAFE_API_KEY, as Elliot planned; no rename. docs.typesafe.ai was not reachable from the build environment.

Thresholds: data/matching.json, propose_at 0.8, abstain_below 0.2, labelled provisional. Jev could not be measured in this build (its key is only on Railway; the build environment cannot reach api.typesafe.ai). Deterministic stage measured on the draft evaluation set: recall at 6 of 0.91, top-1 of 0.80 (memory/verification/2026-11-06-matching-baseline.json). Next: run scripts/evaluate_matching.py with the key, set thresholds from the sweep, and supersede this file.

Legacy seed (deviation from the brief, for Elliot's review): the 2023 ReducedwithWeights match files record a CoFID food against a weight value and a cosine similarity, not against the FPS or sampling record matched, and contain visible algorithmic errors (for example port matched to a portion of hot wings, garlic powder to "1 slice"). Importing them as author-reviewed matches would misstate their provenance, so they were not imported and not used as gold. The author's hand-curated retail list (code and sale format) was imported instead (data/raw/legacy-retail-core-2023). The evaluation set's labels are builder drafts awaiting Elliot's spot-check.

Evidence: tests/test_bulk_matching.py (mock Jev in the documented format; key never echoed; degradation; confirmation basis).
