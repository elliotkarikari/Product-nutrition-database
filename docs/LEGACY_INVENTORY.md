# Legacy tables inventory (`main`, November 5, 2026)

Every data table on `main` of `elliotkarikari/Product-nutrition-database` at commit `cfadc8a`, read from GitHub without changing `main`. Built from the files and their full git history (205 commits since April 2023). Nothing here has been imported into ShelfScale except where a row says so.

## How the tables came to be

- **2023 (repo then named Product_Weight_Project):** notebooks under `Jupter_notebooks/` built every table. Food Portion Sizes was extracted from a PDF of the book with tabula (`Converting Food Portion Sizes PDF to a CSV.ipynb`, May to June 2023). About 20 commits in June 2023 curated the McCance and Widdowson "Reduced" lists group by group ("Cereals Cleaned", "Milk prod cleaned" and so on). The fruit and vegetable sample tables were extracted from the two GOV.UK sampling reports in August 2023.
- **May 12, 2025 (`c535d175`):** everything moved into `Data/` in one commit, so most files' history under their current names starts there.
- **August 17, 2025 (`61b53eed`):** line endings normalised across all tables; no content change (identical ignoring whitespace).
- **August 19, 2025 (`6c9e8d88`):** `Data/Raw Data/` deleted (see "History flags").

## Summary by family

| Family | Files | Derives from | State | In the `shelfscale-open` branch |
|---|---|---|---|---|
| Food Portion Sizes | 5 | The FPS book (3rd edition, FSA, TSO 2002) | See below; one of these is Elliot's hand transcription | Import pending Elliot naming the transcription file (SPEC section 12) |
| Mixed weight tables (`ReducedwithWeights/`) | 8 | FPS, the sampling reports, retailer web pages and similarity matching to CoFID | Matching outputs, sources mixed row by row | **Out.** Retailer web pages are excluded as evidence (SPEC section 6); matching outputs are not raw evidence. Usable privately at the paths below. |
| Sampling-report tables | 76 | The 2011 (DH) and 2015 (PHE) sampling reports, OGL | PDF-extracted, with measured damage | **Snapshotted** as raw evidence: `data/raw/legacy-main-fv-sampling-tables` (byte for byte, checksums in its MANIFEST.json). Not an evidence source; values come from the original reports. |
| CoFID and labelling-derived lists (`MW_DataReduction/`) | 57 | CoFID 2021, and a "Labelling dataset" (CoFID 2019 values recalculated for labelling, gap-filled from manufacturers' data, literature and other countries' tables) | Hand-curated product lists (which foods are sold, sale formats); several carry a third-party reviewer's comments column | **Out.** The labelling dataset's publisher and licence are unconfirmed and its gap-filling mixes sources; the reviewer's comments are never published (Elliot's instruction). Usable privately at the paths below. |
| Header-only placeholders | 122 | n/a | Header row, no data | Out; nothing to keep |

## Food Portion Sizes: the transcription and the other files

| File on `main` (`Data/Processed/FoodPortionSized/`) | Rows | What it is |
|---|---|---|
| `FoodPortionSizes_PDF.csv` | 2,920 | The tabula extraction from the book PDF: index columns, the book's hierarchy split across rows, the PDF's fraction character (U+2044) intact. UTF-8, pandas output. |
| `Processed_Food_Portion_Sizes.csv` | 2,652 | **Elliot's hand transcription of the book, made from his own copy (confirmed by Elliot, November 5, 2026).** Group, Brand, Food Name, Portion Consumed, Weight. The import source for FPS in this branch. |
| `Processed_Food_Portion_Sizes_VJ.csv` | 2,677 | The transcription with a third-party reviewer's annotations and additions, including rows from retailer web pages. **Not a source; never copied, quoted or published in this project** (Elliot's instruction). |
| `FPS_VJ.csv` | 2,677 | Another copy of the annotated file above. Same status: not a source; never copied, quoted or published. |
| `FPS_VJ (version 1).csv` | 2,677 | An earlier edit of the annotated file. Same status: not a source; never copied, quoted or published. |

The three `_VJ` files are listed only so they stay findable on `main`. Nothing from them is in this branch; `tests/test_no_vj_content.py` checks that.

## History flags for Elliot

- **The book itself was in the public repository.** `Data/Raw Data/Food_Portion_Sizes.pdf` was committed in `c535d175` (May 12, 2025) and deleted in `6c9e8d88` (August 19, 2025). Deleting it does not remove it: it is still in `main`'s public history. The FPS decision covers the transcribed weights, not a copy of the book; removing the PDF from history needs a history rewrite of `main`, which is Elliot's call.
- The original CoFID 2021 workbook in the same deleted folder is byte-identical (sha256 `436e9445…`) to ShelfScale's snapshot in `data/raw/uk-cofid-2021`, an independent check on that snapshot.
- An Open Food Facts notebook exists in the 2023 history (`6161753d`). No Open Food Facts table is on `main` now.
- `McCance_Widdowson_Full.csv` has 2,889 rows: the 2,887 CoFID 2021 foods plus two empty rows.

## Every file

Generated from `git ls-tree` of `main` at `cfadc8a`: 268 files under `Data/`.

### FPS (5 files)

| Path on main | Rows |
|---|---|
| `Data/Processed/FoodPortionSized/FPS_VJ (version 1).csv` | 2677 |
| `Data/Processed/FoodPortionSized/FPS_VJ.csv` | 2677 |
| `Data/Processed/FoodPortionSized/FoodPortionSizes_PDF.csv` | 2920 |
| `Data/Processed/FoodPortionSized/Processed_Food_Portion_Sizes.csv` | 2652 |
| `Data/Processed/FoodPortionSized/Processed_Food_Portion_Sizes_VJ.csv` | 2677 |

### Mixed weights (FPS / sampling / retailer web / matching) (8 files)

| Path on main | Rows |
|---|---|
| `Data/Processed/ReducedwithWeights/FV_MatchedFPSnDoh11.csv` | 170 |
| `Data/Processed/ReducedwithWeights/FV_MatchedFPSnDoh15.csv` | 170 |
| `Data/Processed/ReducedwithWeights/RedM&Weight.csv` | 535 |
| `Data/Processed/ReducedwithWeights/dataproduct.csv` | 535 |
| `Data/Processed/ReducedwithWeights/dataproduct2.csv` | 537 |
| `Data/Processed/ReducedwithWeights/dp_full.csv` | 520 |
| `Data/Processed/ReducedwithWeights/fv_full.csv` | 169 |
| `Data/Processed/ReducedwithWeights/matchedwithFPS.csv` | 511 |

### Sampling reports (snapshotted) (76 files)

| Path on main | Rows |
|---|---|
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Banana.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Broccoli.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Cabbage.csv` | 6 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Cannedtomatoes.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Carrot1.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Carrot2.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Cauliflower.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Cucumber.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/GreenBeans.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Lettuce.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Melon.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Mushroom.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Oldcarrot.csv` | 6 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Onion.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Oranges.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Pakchoi.csv` | 6 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Pear.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Potatoes1.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Potatoes2.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Strawberry.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/Tomatoesraw.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/apple.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/peasf.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/redpeppers.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/sweetcorn.csv` | 9 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2011/yellowpepper.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Apricots.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Asparagus.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Aubergine.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Avocadopear.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Beetroot.csv` | 4 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Blackberries.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Broadbeans.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Brusselsprout.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/ButternutSquash.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Cannellini.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Celery.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Chickpeacanned.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Courgettes.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Curlykale.csv` | 1 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Edamame.csv` | 7 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Fig.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Grapefruit.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Haricot.csv` | 6 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Kiwi1.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Leek.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Mangetout.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Okra.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Papaya.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Prunes.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Radish.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Raisins.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Red kidneyboil.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Red kidneycanned.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Rhubarb.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Runner beans.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Swede.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Sweetcorn.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Sweetpotato.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Watercress.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/Yam.csv` | 8 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/cherries.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/lentils.csv` | 19 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/mango.csv` | 10 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/nectarines.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/parsnip.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/pineapple.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/plum.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/2015/raspberry.csv` | 11 |
| `Data/Processed/Fruit and Veg Sample reports/tables/Combined_Fruit_Veg_Samples.csv` | 80 |
| `Data/Processed/Fruit and Veg Sample reports/text/DofHealth_text_FV2011.csv` | 958 |
| `Data/Processed/Fruit and Veg Sample reports/text/PHealth_text_FV2015.csv` | 622 |
| `Data/Processed/Fruit and Veg Sample reports/text/Raw_Fruit_Veg_Samples.csv` | 566 |
| `Data/Processed/Sample Reports/DOH2011.csv` | 958 |
| `Data/Processed/Sample Reports/PH2015.csv` | 437 |
| `Data/Processed/temp/fruit_veg_survey.csv` | 283 |

### CoFID / labelling-derived lists (57 files)

| Path on main | Rows |
|---|---|
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_A.csv` | 29 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_B.csv` | 118 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_C.csv` | 115 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_D.csv` | 15 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_E.csv` | 5 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_F.csv` | 22 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_G.csv` | 19 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_H.csv` | 12 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_I.csv` | 4 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_J.csv` | 4 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_K.csv` | 10 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_L.csv` | 25 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_M.csv` | 42 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_N.csv` | 5 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_O.csv` | 16 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_P.csv` | 50 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_Q.csv` | 3 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_R.csv` | 17 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_S.csv` | 42 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_T.csv` | 23 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_V.csv` | 6 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_W.csv` | 10 |
| `Data/Processed/MW_DataReduction/Reduced Individual Tables/Reduced_Y.csv` | 5 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Alcoholic beverages.csv` | 8 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Beverages.csv` | 14 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cereals and cereal products.csv` | 89 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Alcoholic beverages_Cleaned.csv` | 8 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Beverage_Cleaned.csv` | 14 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Cereals_Cleaned.csv` | 89 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Eggs_Cleaned.csv` | 2 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Fats and oils_Cleaned.csv` | 7 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Fish and fish products_Cleaned.csv` | 33 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Fruit_Cleaned.csv` | 68 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Herbs and spices_Cleaned.csv` | 35 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Meat and meat products_Cleaned.csv` | 46 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Milk and milk products_Cleaned.csv` | 33 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Nuts and seeds.csv` | 17 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Reduced_SecondClean.csv` | 535 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Soups, sauces and miscellaneous foods_Cleaned.csv` | 44 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Sugars, preserves and snacks_Cleaned.csv` | 25 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Cleaned/Vegetables_Cleaned.csv` | 114 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Eggs.csv` | 2 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Fats and oils.csv` | 7 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Fish and fish products.csv` | 33 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Fruit.csv` | 68 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Herbs and spices.csv` | 35 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Meat and meat products.csv` | 46 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Milk and milk products.csv` | 33 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Nuts and seeds.csv` | 17 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Soups, sauces and miscellaneous foods.csv` | 44 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Sugars, preserves and snacks.csv` | 17 |
| `Data/Processed/MW_DataReduction/Reduced Super Group/Vegetables.csv` | 114 |
| `Data/Processed/MW_DataReduction/Reduced Total/McCance_Widdowson_Full.csv` | 2889 |
| `Data/Processed/MW_DataReduction/Reduced Total/RedLab2021_withComments.csv` | 597 |
| `Data/Processed/MW_DataReduction/Reduced Total/Reduced_Labelling2021.csv` | 1791 |
| `Data/Processed/MW_DataReduction/Reduced Total/Updated3_RedLab2021.csv` | 511 |
| `Data/Processed/MW_DataReduction/Reduced Total/Updated_RedLab2021.csv` | 582 |

### Header-only placeholders (122 files)

Header row only, no data. `A.csv`, `AA.csv`, `AB.csv`, `AC.csv`, `AD.csv`, `AE.csv`, `AF.csv`, `AG.csv`, … (full list via `git ls-tree`).

