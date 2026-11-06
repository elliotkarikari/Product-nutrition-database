# Official milk and beef overlays

Status: active
Decision maker: Codex, under Elliot’s Phase 4 mandate. Date: 2026-11-05.

Decision: ingest the official milk analytical HTML table and beef results ODS using checksum-verified snapshots. Apply only explicitly reviewed exact/established food matches and equivalent nutrient definitions; retain unmatched observations separately. Preserve original CoFID observations with reciprocal per-value supersession and expose provenance in assessment inputs. Below-limit values remain bounds; unmeasured cells never replace data.

Reasoning: milk ODS contains label information, not the laboratory results. Cooking, fat bands and season identities cannot be guessed. Beef vitamin D activity uses a different metabolite multiplier from CoFID, so its total has a separate definition and does not overwrite CoFID VITD.

Evidence: docs/OVERLAY_IMPORT_REPORT.md; data/overlays/matches.json and beef-columns.json; source URLs/checksums in the two raw MANIFEST.json files; tests/test_overlays.py. Eight milk foods and three beef foods receive updates; unmatched coverage is not implied.
