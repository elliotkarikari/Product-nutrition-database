# ShelfScale Open

ShelfScale Open is an open-source food nutrition data engine. It matches foods and recipes to trustworthy composition data, keeps the evidence attached to every value, and turns that evidence into country-specific outputs such as nutrition declarations, front-of-pack colours and regulatory scores.

The first country pack is the United Kingdom.

## Why this exists

Food nutrition data is scattered across spreadsheets, PDF reports, product labels, commercial catalogues and national food tables. The rules that interpret the data also change by country, and sometimes by nation inside a country. ShelfScale separates the two problems:

- **Canonical core:** food identity, matching, ingredients, nutrient observations, weights, portions, yields and provenance.
- **Country packs:** the dataset, nutrient definitions, label rules, scoring models, allergen lists, language and presentation rules for one market.

## Product principles

1. **Portion first.** People eat portions, items and packs, not 100 g. Per 100 g remains available because it is the comparison and compliance basis.
2. **No silent numbers.** Every nutrient value carries its source, version, date or period, method, jurisdiction and confidence.
3. **No silent updates.** A changed source creates a candidate release with a diff. It does not overwrite the current release.
4. **Licence before ingestion.** Open-source code does not make every dataset open. Each source is registered with its permitted use before data is imported or redistributed.
5. **Estimates say so.** A lab analysis, a manufacturer specification, a generic table value and a crowd-sourced label are not presented as if they were the same kind of evidence.

## First build slice

- UK canonical import for CoFID.
- A faithful UK Nutrient Profiling Model 2004/05 scorer, tested against published worked examples and boundary fixtures, with NPM 2018 beside it as a shadow model.
- UK traffic lights.
- Portion and per-item views built from portion-size and unit-weight evidence.
- A source register and watcher process for official updates, including category reports published between CoFID editions.

## Repository layout

- `src/shelfscale/` - the engine.
- `docs/` - product, architecture, data model and update process.
- `data/source-register.yaml` - machine-readable register of watched sources and licence status.
- `tests/` - scorer and pipeline tests.

## Licence boundary

The code in this repository is MIT licensed. Data is different: every dataset keeps its own licence and attribution terms. A source marked `reference-only` or `licence-required` must not be redistributed as part of a ShelfScale data release.

## Status

Working engine and API, November 2026. The governing document is `SPEC.md`. Built and tested: the UK NPM 2004/05 scorer (validated against the guidance's six worked examples), the NPM 2018 scorer as a shadow model, not in force (validated against DHSC's 17 worked examples; 2018 scores need the caller's free sugars figure), dual scoring of both models in every API result, front-of-pack traffic lights from the 2016 FoP guidance, an assessment API with supplied and CoFID lookup modes (`docs/API.md`), the CoFID 2021 importer, unit weights from the 2011 and 2015 fruit and vegetable sampling reports, and 2,606 typical portions from Food Portion Sizes (2002), published on Elliot's decision; Crown copyright, NOT covered by the Open Government Licence. Official milk (2022–23) and beef (2024) overlays now preserve per-value supersession and assessment provenance; see `docs/OVERLAY_IMPORT_REPORT.md`. Reviewed 2018 tuber exclusions and model-specific FVN flags are implemented. Railway config and required-key authentication, a shared 60/minute limit, and a public service summary are implemented. The hardening push is held until Elliot confirms the Railway key is deployed; `memory/build_memory.md` records the live state. Recipe calculation, label export, CSV tooling and watcher code remain specified, not built. Two activities run outside this code, a monthly source watch over the registered data sources and daily research on data sources and product forms: they run in Rocky's agent environment, outside this repository, and their schedules and logs are held there. Nothing in this repository can show whether they are running. Both report for human review and change no data by themselves.
