# FVN derivation and the Phase 4 rulings

Status: active
Decision maker: Elliot (rulings in current mandate); Codex (explicit code selection and flag structure under delegated authority). Date: 2026-11-05.
Supersedes: fvn-derivation.md. All its 2004/05 derivation rules remain in effect.

Decision: retain caller overrides, DA 0, DR unknown and other D/F/G derivation. For 2018 only, the reviewed DG codes in src/shelfscale/fvn.py derive 0: Jerusalem artichoke, sweet potato, yam, cassava, taro tubers and plantain. Taro leaves remain eligible. Runtime uses codes, never name guesses. Explicit fvns_g wins, then caller fvn_percent with the 2004/05-definition limitation label, then the group/code rule. GA flags distinguish seed exclusion under 2004/05 from inclusion under 2018; FA processing review remains. Caller input removes the corresponding derivation flag, not its unverified-caller label.

Reasoning: the official 2018 definitions exclude the named tubers and the technical guidance also names plantain. Seeds now count, so the old warning must not imply they are excluded under both models. No model table or official example changes.

Evidence: https://www.gov.uk/government/publications/nutrient-profiling-model-2018/nutrient-profiling-model-2018-fruit-vegetables-nuts-and-seeds-definitions (Tubers; Seeds); technical guidance, What is not included. Code/name list reviewed against CoFID 2021. Less explicit identities (e.g. matoki, tannia, arrowhead, lotus tubers) remain a review question; do not silently invent species equivalence.

Identity remains repository-configured Elliot. VJ policy remains fix-forward: never import/quote prohibited material; no main history rewrite. No change to the corresponding standing decisions.
