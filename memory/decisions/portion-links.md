# One-tap portion weights

Status: active

Decision date: 2026-11-06

Decision maker: the implementing agent, extending the existing exact-name rule; recorded for Elliot's review.

Decision: A one-tap weight is offered only when the portion record links to the CoFID food by exact name (case and spacing ignored, one unique match), the rule FPS already uses. The fruit and vegetable sampling reports are linked the same way. A sampling weight with an edible proportion is offered as the edible part (mean whole weight x mean edible proportion, labelled "calculated"), because CoFID values are per 100 g of edible portion. FPS ranges, alternatives and volumes are listed but not tappable. No fuzzy or near-name link is made.

Effect: 52 of 2,887 foods have a one-tap weight. Bananas, for example, have a sampling weight under a different name and get none.

Reasoning: SPEC section 8 and DATA_MODEL keep matching a reviewed step; guessing links would put unreviewed weights behind a single tap.

Evidence: src/shelfscale/ui_api.py _portions; tests/test_ui.py TestPortionsAndProvenance.

Next: a reviewed portion-to-food mapping (like overlays/matches.json) is the way to widen coverage.
