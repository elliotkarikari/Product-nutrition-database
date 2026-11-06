# Official milk and beef overlays

Verified 2026-11-05 by Codex. Sources are snapshotted byte-for-byte with URLs, retrieval timestamps, OGL attribution and SHA256 in `data/raw/uk-milk-2022-23` and `data/raw/uk-beef-2024`. Import: `src/shelfscale/overlays.py`; format readers: `source_tables.py`. No dependencies added.

Milk: OHID/Quadram report updated 17 September 2025, sampling August–September 2022 and February 2023. The ODS annex contains product labels, NOT laboratory results. Laboratory Table 4 in report.html supplies 18 food/season rows × three nutrients = **54 observations**: riboflavin, vitamin B12, iodine. The published seasonal average is used verbatim, never recalculated from rounded seasonal cells. **24 observations update eight CoFID entries**; 30 remain source-only. Other nutrients remain CoFID. Summer-only samples are not silently equated with CoFID summer-and-autumn entries.

Beef: DHSC/Quadram publication 2 October 2026; samples bought in 2024. Official results ODS contains 25 composite foods. The workbook's cover says 25 September 2026; the release edition uses the publication page date. General analyses ran June–October 2024; iodine and vitamin D analyses November 2025–February 2026. Collection and analysis periods remain distinct. All ten nutrient tables are read; the repeated fatty-acid totals in Macronutrients are read from Total_fatty_acids once. **5,672 observations**, with **153 unmeasured [x] cells excluded**. **689 observations apply to three CoFID entries**, 4,983 remain source-only. Source-only observations are returned by import_overlays().source_only for inspection; the HTTP lookup remains CoFID-code based.

## Matching and definitions

`data/overlays/matches.json` is the reviewed food-match register. Exact names match, plus two established equivalences: unseasoned UHT CoFID entries to the report's UHT averages; raw rump “lean” to “lean only”. No fat-band, cut, cooking-method or doneness guesses. Unmatched composites are retained, not discarded or relabelled. Beef maps only raw rump lean (18-043), raw fillet lean/fat (18-017), raw sirloin lean/fat (18-065).

`data/overlays/beef-columns.json` explicitly maps source columns to nutrient definitions. Identical fatty-acid descriptions/bases map to CoFID codes; extra fractions retain BEEF-prefixed definitions. Factors retain food_factor basis. Unit/basis mismatch fails. New source definitions do not overwrite superficially similar old definitions.

**Vitamin D definition difference:** CoFID 2021 user guide defines meat VITD as D3 + 5 × 25OHD3; the beef report uses D3 + 2.5 × 25OHD3. The new total is `BEEF:VITD_activity_2.5`, never silently substituted for VITD. Measured component definitions still supersede equivalent CoFID components. The original compiled VITD remains identified as CoFID, not recomputed from mixed dates.

## Provenance and supersession

The raw CoFID import stays immutable. Runtime composition creates current/superseded observations with reciprocal IDs for each matched food/nutrient, never whole-row replacement. Unmeasured [x] retains the original value. Below-limit results remain `below_limit` with value null and the published bound in value_text; no zero or invented central estimate is used. Calculated protein/energy/fatty-acid totals are labelled calculated_from_laboratory_analysis; published milk averages are labelled published_seasonal_mean.

Lookup returns the composed data_release identifier and both current and superseded observations. Each carries release URL/hash/attribution, method, food identity, table/row/column, collection/analysis period, confidence and supersession links. Assessment inputs reference the exact current observation; 2018 salt derived from sodium retains sodium provenance. Free sugars still come only from the caller. Milk micronutrients are visible among observations, not falsely described as NPM inputs.

Validation: tests/test_overlays.py covers raw source cells, counts, immutable base, reciprocal links, unmeasured/below-limit values, definition differences, changed-snapshot refusal and provenance in both model inputs. Tests/test_fvn_rulings.py covers all 22 reviewed DG exclusions, leaves, overrides and model-specific flags.
