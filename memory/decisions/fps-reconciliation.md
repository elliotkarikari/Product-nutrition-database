# FPS reconciliation identity

Status: active
Decision maker: Codex, under Elliot’s Phase 4 mandate. Date: 2026-11-05.

Decision: key reconciliation by group, brand, food and portion text; preserve ordered words and repeated words. Require unique extraction candidates and never reuse an extraction row. Record reviewed mappings and unresolved ambiguity explicitly. Retain all original transcription weights.

Reasoning: word sets confused meat components with beans and loose matching hid duplicate pork descriptions. Three of the six apparent disagreements were wrong extraction-row comparisons. Two weight differences remain; pork is unresolved without the physical book.

Evidence: scripts/reconcile_fps.py; data/reconciliation/fps-review.json; docs/fps_reconciliation.csv; docs/FPS_IMPORT_REPORT.md; tests/test_fps.py. No licensing or publication decision changed.
