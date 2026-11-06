---
type: data-model
status: draft
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Data model

The core rule: **a nutrient value is never stored bare.** It is an observation with evidence.

## Entities

### Source
A publisher or data provider: name, organisation, homepage, licence, terms checked date, contact or access route.

### DatasetRelease
One versioned publication from a source: version label, published date, retrieved date, file hash, licence snapshot, status (current, superseded, candidate).

### Food
A generic food or ingredient identity: canonical name, aliases, country-pack names, category, form (raw, cooked, dried, reconstituted), edible portion factor.

### Product
A specific market item: GTIN where one exists, brand, manufacturer, pack size, market and jurisdiction availability, label text as supplied.

### NutrientObservation
One nutrient value for one food or product:

- nutrient code and definition version (definitions differ by country and method);
- value and unit;
- basis: per 100 g, per 100 ml, per portion, per item;
- state: as sold, as prepared, as consumed;
- method: laboratory analysis, manufacturer specification, label transcription, calculation, estimation;
- source and dataset release references;
- collection or analysis period, where known;
- confidence and status;
- supersedes and superseded-by links.

### PortionObservation
A portion or unit weight: grams, basis (typical portion, weighed sample mean, manufacturer serving), sample size and spread where known, source and period. A mean without its spread is a weaker observation and is labelled as such.

### MatchDecision
Links a named item (recipe line, loose item, product name) to a food or product record: method (exact, rule, fuzzy, model-assisted, human), confidence, reviewer where human, frozen release reference.

### Recipe
A versioned list of ingredient match decisions with quantities and preparation state, owned by a user or business. Recipe calculations are derived observations and keep their input references.

### CountryPack
A versioned bundle: dataset references, nutrient definitions, label rules, scoring models, allergen list, language files and attribution text.

### ScoreResult
A calculated output: model and version, input observation references, data release, pack version, result, and the basis used. A score without its input references is not a valid ShelfScale output.

## CoFID 2021 import: where the real files and this model differ

Found while building the importer (November 5, 2026). Each is resolved in the code and tested; none is hidden.

| Conflict | Resolution |
|---|---|
| CoFID food codes are not unique: code `13-669` names two different foods (roasted aubergine, row 55; raw watercress, row 2827), with different values. | `Food.food_id` is the code where it is unique and `code@row<n>` for every row sharing one. `Food.source_code` keeps the code as published. Lookups by code return a list. |
| Food names are not unique either (for example "Beef, mince, stewed" appears under two codes). | Lookups by name return a list, with a note when more than one food matches. |
| The model's basis list has no basis for the fatty-acid columns labelled "/100g FA", nor for the Factors sheet (edible proportion, specific gravity and other factors). | Two basis values added: `per_100g_fatty_acids` and `food_factor`. Alcoholic beverages (food group Q) are `per_100ml`, as the dataset's notes state. |
| CoFID does not record a method per value. Values are compiled from analysis, literature, calculation and estimation, with the main source given per food. | `method` is `compiled_food_table`, and `Food.main_data_reference` carries CoFID's own per-food source. |
| CoFID does not record state per value; raw, cooked or prepared is part of the food name. | `state` is `as_described_in_food_name`. |
| No collection or analysis period per value. | Left empty, as the model allows ("where known"). |
| Values are not always numbers: `Tr` (trace), `N` (present, amount unknown), and 14 values written in brackets, which the 2021 guide does not define. | `value_kind` is `trace`, `present_not_quantified` (both with no number) or `number_bracketed` (number kept, flagged). `value_text` always keeps the source text. |
| The user guide says alcohol (ALCO) values are g per 100 ml without saying whether that applies only to alcoholic beverages. | Followed the dataset's general note: per 100 ml for group Q only. Flagged for review. |
| NSP (Englyst) and AOAC fibre are different nutrients by different methods. | Separate observations, `method` `nsp_englyst` and `aoac`; never merged or converted. |


## Fruit and vegetable sampling reports: where the reports and this model differ

Found while importing the 2011 (DH) and 2015 (PHE) sampling reports (November 5, 2026). Each is resolved in `src/shelfscale/fv_samples.py` and tested.

| Conflict | Resolution |
|---|---|
| The reports do not publish individual item weights. Each sub-sample's weight is already the average of several items (for bananas, 6 per sub-sample). | `PortionObservation.sample_size` counts sub-samples, and the spread (min, max, mean, sd) is between sub-sample averages. The report's own wording of how many items each sub-sample holds is kept in `SampleComposite.preparation_note`. |
| Tables differ from food to food (different columns, `N/A` cells, wrapped text, sub-groups, stated averages that cover only part of the table). Column meanings cannot be read reliably from the headers. | A food is imported only when the mean of its table's first weight column reproduces the report's own stated average within 0.1 g. Edible portions are imported only when they reproduce the stated average edible portion within 0.01. 44 of 69 tables pass; the other 25 are listed with the reason and nothing is imported from them. |
| The model puts an edible-portion factor on `Food`. The reports give it per sub-sample. | Kept per sub-sample (`SubSample.edible_portion`) and summarised on the observation, only when it reconciled. |
| `PortionObservation` needs a period; the reports give purchase dates per sub-sample, not a period. | Period is the earliest to latest purchase date of the composite's sub-samples, as printed. Two dates (sweet potato, papaya) fall in early 2015, before the 2015-16 fieldwork; they look like year typos in the report and are kept as printed. |
| The composite names are the reports' own and are not CoFID food codes. | Not linked to CoFID yet. Matching is its own step (SPEC section 8); no link is guessed here. |
| The legacy processed CSVs that pointed to these reports are damaged by PDF extraction. | Not used as evidence. Values come from the original reports; the manifests record the legacy route and the damage. |

## Food Portion Sizes: a typical portion is not a sample

Found while importing Food Portion Sizes (November 5, 2026).

| Conflict | Resolution |
|---|---|
| `PortionObservation` here is shaped for weighed samples (composite, sub-samples, spread). FPS gives one typical weight per portion, with no sample behind it in the data. | A separate record, `TypicalPortion` (basis `typical_portion`), holds the food name as printed, group, brand, portion description, the weight text exactly as transcribed, and how it was read. Two shapes for two kinds of evidence; neither carries fields it cannot fill. |
| Some FPS weights are not one number of grams: volumes in ml, alternatives ("250/300g"), a range, and four unreadable values with a letter l for the digit 1. | `value_kind` says which; only a single gram value sets `grams`. Volumes are not converted (no density); alternatives and ranges keep every number without choosing; unreadable values are reported and not imported. |
| FPS names products and brands as the book prints them, not as CoFID foods. | Matched to CoFID by exact name only (69 rows); the rest stay FPS-only rather than forcing a match. |


## Implemented overlay observations

NutrientObservation now carries collection period, analysis period, source locator/food, confidence and reciprocal supersession IDs. lookup returns current and superseded values; scoring selects current only. Different nutrient definitions (notably beef total vitamin D activity) remain separate. See OVERLAY_IMPORT_REPORT.md.
