# Never round before banding

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; SPEC §12.

Decision: Band the supplied, looked-up or converted values without rounding. Presentation rounding happens only after scoring.

Reasoning: The recorded milkshake example crosses the saturated-fat boundary when the exact mixture is used. An unstated rounding assumption must not determine the result.

Evidence: SPEC.md §12; docs/API.md, Scoring basis; src/shelfscale/service.py assess_values; tests/test_density.py. Code inspection and suite passed; official guidance was not independently re-fetched this round.
