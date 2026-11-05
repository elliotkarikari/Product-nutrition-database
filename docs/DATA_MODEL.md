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
