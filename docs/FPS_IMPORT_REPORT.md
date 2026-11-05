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

| Result | Rows |
|---|---|
| Agree: same words, same weight | 941 |
| Agree: words contained in one extraction record, same weight | 165 |
| Weight differs only by OCR characters (I or l for 1, O for 0, m1 for ml) | 77 |
| Same words, but one side has no weight | 21 |
| **Different weight for the same food and portion** | **6** |
| Transcription row not located in the extraction | 1,442 |
| Extraction record with a weight not claimed by any transcription row | 1,246 |

The six real disagreements (transcription weight used):

| Transcription row | Food and portion | Transcription | Extraction |
|---|---|---|---|
| 1411 | Ice-cream, tub | 60g | 61g (row 1593) |
| 1566 | Burgerbites in baked beans, burgerbites, small tin | 55g | 170g (row 1726) |
| 1570 | Chickbits, in baked beans, chickbits, small tin | 55g | 170g (row 1730) |
| 1770 | Pork chops, edible portion | 110g | 85g (row 1946) |
| 1915 | Stock cube, Oxo, 1 | 6g | 7g (row 2099) |
| 2301 | Baked beans, with sausage, sausage, small can | 55g | I70g (row 2526) |

The three 55g against 170g cases look like the component (the burgerbites, chickbits or sausage in a tin) against the whole tin. Only the book can settle them.

**What this check cannot show.** The transcription shares character-level OCR artefacts with the extraction (for example "m1s" for "mls", "I" for "1", "l00g", and the same "3. 8g"). The two files are therefore not independent: where they agree, they may agree because one was built from the other. The 1,442 "not located" rows are mostly names restructured in the transcription (brand, food and portion split differently from the book's layout), not missing data; the 1,246 unclaimed extraction records are the other side of the same restructuring plus extraction noise. Both lists are in the CSV for checking against the book.
