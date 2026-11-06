# Free-sugars honesty

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; SPEC §7.

Decision: Require caller-supplied free_sugars_g for NPM 2018 and label its origin. Never substitute total sugars or produce an indicative score from them. Missing free sugars means not scorable under 2018.

Reasoning: CoFID total sugars do not provide the required free-sugars quantity. A labelled missing input is more honest than a fabricated score.

Evidence: SPEC.md §7; src/shelfscale/cofid_assess.py _npm2018_for_food; src/shelfscale/service.py; tests/test_dual_scoring.py (supplied, lookup and bulk).
