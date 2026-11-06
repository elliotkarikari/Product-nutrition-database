# Finite inputs and bounded request parsing

Status: active
Decision maker: Codex under Elliot's audit-remediation mandate. Date: 2026-11-05.
Decision: reject non-finite, boolean, negative nutrient and overflowed numeric values; require positive portions/density. Reject ambiguous HTTP framing and invalid JSON constants, with 10-second socket reads and existing 5 MB cap. All four POST routes will require the Phase 5 key because all can compute assessments.
Reasoning: invalid inputs must not become plausible scores or disconnects. Shared validation protects single and bulk paths without changing valid scoring bands.
Evidence: docs/CODEX_AUDIT.md findings 1–3; tests/test_input_boundaries.py. No new dependencies.
