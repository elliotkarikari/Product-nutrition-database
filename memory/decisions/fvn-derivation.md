# FVN derivation

Status: active

Decision date: 2026-11-05

Decision maker: Elliot Karikari; SPEC §12.

Decision: Caller fvn_percent wins. DA* derives 0 with excluded_by_guidance; DR does not derive. DB, DF, DG, DI, FC, GA and FA retain 100% derived_from_group pending review. Never infer a percentage from a food name.

Reasoning: CoFID has no FVN percentage. Composite dishes cannot justify the same inference as a group; seeds and sugared/syrup fruit require review.

Evidence: SPEC.md §12; docs/API.md; src/shelfscale/cofid_assess.py. Actual implementation uses broad D/F/G prefixes after DA/DR exclusions. Review flags are documented, not emitted as structured API flags. 2018 tuber/seeds decisions remain open in SPEC; do not silently treat a queued ruling as implemented.
