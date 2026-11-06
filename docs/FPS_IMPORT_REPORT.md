# Food Portion Sizes import report (November 5, 2026)

Source: Food Standards Agency (2002), *Food Portion Sizes*, 3rd edition, TSO, ISBN 9780112429616. Crown copyright; **NOT covered by the Open Government Licence**; included on Elliot's decision of November 5, 2026 (`data/raw/uk-food-portion-sizes-2002/DECISION.md`). Import source: Elliot's transcription, `Processed_Food_Portion_Sizes.csv` from `main` at `cfadc8a`, snapshotted unchanged (sha256 `d47ea650…`). Importer: `src/shelfscale/fps.py`. Tests: `tests/test_fps.py`.

## Counts

| | Rows |
|---|---|
| Rows in the transcription | 2,652 |
| Imported as typical portions | 2,606 |
| of which a single gram weight | 2,575 |
| of which alternatives (for example "250/300g"), numbers kept, none chosen | 19 |
| of which a volume in ml, kept as ml (no density assumed) | 11 |
| of which a range ("350-500g") | 1 |
| Not imported: cross-references ("see ...") | 41 |
| Not imported: no weight given (row 1465, "Bacon") | 1 |
| Not imported: weight not readable as written, not corrected | 4 |
| Matched to a CoFID 2021 food by exact name | 69 rows, 42 CoFID foods |
| FPS-only (no exact CoFID name) | 2,537 |

Unreadable weights, kept as written and not imported: row 24 "3. 8g" (Junior Drink); row 45 "l00g" (Sherry, large); row 2258 "50g/l00g" (Tortilla Chips); row 2261 "25g/50g/l00g" (Twiglets). A letter l stands where the digit 1 belongs. Correcting them is a change to the transcription, which is Elliot's to make.

CoFID matching is exact name only. The legacy matching outputs on `main` were not used: they record a CoFID code with an FPS weight but not which FPS row it came from, and their similarity scores go as low as 0.47 with visibly wrong pairs.

## Reconciliation with the tabula extraction (check only)

Script: `scripts/reconcile_fps.py`; full row-by-row output: `docs/fps_reconciliation.csv`. The extraction (`FoodPortionSizes_PDF.csv` on `main`) is never an import source; where the two disagree the transcription is used.

The reconciliation is now keyed by `(group, brand, food name, portion)` (JSON in `identity_key`), never by transcription row number. Row numbers remain source locators. Word order and repeated tokens are preserved; ambiguous candidates remain unresolved and an extraction row cannot be reused. Explicit reviewed matches live in `data/reconciliation/fps-review.json`. Removing the old word-set/subset heuristics deliberately reduces apparent coverage.

| Result | Rows |
|---|---:|
| Same ordered words and weight | 793 |
| Reviewed food/portion match, same weight | 3 |
| OCR-character weight difference | 58 |
| One side has no weight | 19 |
| Apparent weight disagreement | 2 |
| Ambiguous extraction matches | 8 |
| Ambiguous pork portion | 4 |
| Transcription not located | 1,765 |
| Unclaimed extraction weights | 1,550 |

## Review of the six previously reported disagreements

| Food and portion key | Previously compared | Corrected finding |
|---|---|---|
| Ice-cream / tub | 60g vs 61g, extraction 1593 | Apparent difference remains; book check required. |
| Burgerbites in baked beans, burgerbites / small tin | 55g vs 170g, extraction 1726 | Wrong component: 1726 is beans; following 1727 is burgerbites 55g. Agreement. |
| Chickbits, in baked beans, chickbits / small tin | 55g vs 170g, extraction 1730 | Wrong component: 1730 is beans; following 1731 is chickbits 55g. Agreement. |
| Pork chops, edible portion / unspecified | 110g vs 85g, extraction 1946 | Ambiguous subtype. Extraction has multiple edible-portion entries (1946 85g, 1950 140g, 1953 hOg). No defensible unique match; all four transcription entries with this key remain unresolved. |
| Stock cube / Oxo, 1 | 6g vs 7g, extraction 2099 | Apparent difference remains; book check required. |
| Baked beans, with sausage, sausage / small can | 55g vs I70g, extraction 2526 | Wrong component: 2526 is beans; following 2527 is sausage 55g. Agreement. |

The previous claim of six real disagreements was unsupported by row context. No transcription/imported weight has changed. Shared OCR artefacts mean agreement is not independent book verification; the extraction remains a check only. Raw extraction SHA256 is pinned in the script and snapshot manifest. Reproduce using the read-only `git show` command in the script, then run the script on that file. The six review decisions use food/portion identities, with extraction rows only as evidence locators.
