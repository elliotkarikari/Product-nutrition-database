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

