---
type: product-spec
status: draft-for-review
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# ShelfScale Open: Specification v0.1

Status: **specification first, with two tested prototypes.** Elliot directed on November 5, 2026 that the product does not need to be fully built yet. This document is the build-ready spec. Three components exist and are tested: the NPM scorer (section 7), the single/bulk assessment API (section 13), and the CoFID 2021 importer with a service-level lookup (section 11, step 1). Everything else is specified, not built. Two activities run outside the code: a monthly source watch (section 9) and daily research on data sources and product forms (added November 5, 2026); they run in Rocky's agent environment, outside this repository, and their schedules and logs are held there. Nothing in this repository can show whether they are running.

## 1. Purpose

ShelfScale Open is an open-source food nutrition data engine. It matches foods, loose items, products and recipes to the best available composition evidence, keeps the evidence attached to every value, and applies one country's rules at a time to produce nutrition declarations, front-of-pack colours and regulatory scores.

It exists because the underlying work is currently manual and fragile: national food tables in spreadsheets, one-off government analysis reports in PDFs, commercial product catalogues behind licences, and country rules that change independently of the data.

## 2. Users (ranked by the current-needs research, November 5, 2026)

Full report: `docs/CURRENT_NEEDS_2026-11-05.md`.

1. **Manufacturers and brands in HFSS categories** (confectionery, cereals, soft drinks, snacks, ready meals, bakery), including SMEs supplying retail. Highest urgency and proven ability to pay: their products are scored for placement, promotions and, since January 2026, advertising eligibility, and retailers demand the data from them.
2. **Retailers, wholesalers and symbol groups**, the legally obligated parties for promotion and placement. Large chains are served by Brandbank and productDNA; the independent and symbol long tail is not. The ACS told the NPM 2018 consultation that the absence of a standardised NPM calculator increases inconsistent interpretation and duplicated effort.
3. **Small producers selling prepacked food** (farm shops, market producers moving online or into wholesale). Steady need, price-sensitive: calculated database analysis is the legal alternative to laboratory testing per product.
4. **Bakeries, delis and sandwich shops selling PPDS foods.** Their legal need under Natasha's Law is the product name and a full ingredients list with allergens emphasised. A nutrition declaration is NOT required on PPDS, so this segment is served through ingredient ordering and allergen derivation from recipes, never by selling them nutrition scoring as a legal duty.
5. **Public-sector menu teams** (school catering first; updated England School Food Standards land September 2027). Served largely through catering contracts today; a later segment.
6. **Researchers and app builders.** Low direct pay, high strategic value: they are the open-source distribution engine.

Timing evidence behind the ranking: England volume-promotion rules in force October 2025; UK-wide advertising restrictions in force January 2026; Wales in force March 2026; Scotland in force October 2026; Northern Ireland consulted through October 2026; and DHSC consulted in 2026 on replacing the 2004/05 model with NPM 2018, which would force every in-scope product to be rescored.

## 3. Scope

In scope for the UK pack v1:

- Generic food and ingredient matching against CoFID.
- Loose and own-made item matching, with unit weights and edible-portion conversion.
- Recipe calculation from matched ingredients.
- UK nutrition declaration values, front-of-pack traffic lights, and NPM 2004/05 scores.
- Portion-first presentation: per portion and per item as eaten, with per 100 g shown and labelled as the compliance basis.
- Versioned data releases with provenance on every value.

Out of scope for v1:

- Any non-UK country pack.
- Laboratory analysis or claims that estimates are lab results.
- Legal advice or a compliance guarantee.
- Bulk scraping of sources whose terms forbid it.
- A consumer diet or calorie-tracking app.

## 4. Architecture

Two layers, as decided November 5, 2026:

- **Canonical core:** food and product identity (including GTIN), ingredients and recipes, nutrient observations, portion and unit-weight observations, cooking yields, edible-portion factors, and match decisions. Country-neutral.
- **Country pack:** one per market. Holds the official composition dataset and overlays, nutrient definitions and methods, label fields and order, rounding, reference intakes, allergen list, scoring models, front-of-pack scheme, language and portion conventions, and the licence and attribution text for every source it uses.

The UK pack carries an internal jurisdiction layer (England, Scotland, Wales, Northern Ireland) because HFSS promotion and placement rules differ by nation.

Detail: `docs/ARCHITECTURE.md` and `docs/DATA_MODEL.md`.

## 5. Data model rules

1. A nutrient value is never stored bare. It is an observation carrying: nutrient definition version, value, unit, basis (per 100 g, per 100 ml, per portion, per item), state (as sold, as prepared, as consumed), method (laboratory analysis, manufacturer specification, label transcription, calculation, estimation), source and dataset release, collection or analysis period where known, confidence, and status (current, superseded, estimate).
2. Portion observations keep sample size and spread where known. A mean without a spread is labelled weaker evidence.
3. Match decisions are data. Once reviewed they are frozen into a release and superseded by new decisions, never rewritten.
4. Every score or label output records the data release, country pack version and input observations that produced it.

## 6. Data sources and licence gates

The register is `data/source-register.yaml`, explained in `docs/DATA_SOURCES.md`.

**Source policy (Elliot, November 5, 2026): legitimate, defensible sources only.** Every value in the product must trace to a source we can defend line by line: an official dataset or analysis, a manufacturer's own specification or current label, or data held under a licence that permits the use. Crowd-sourced and community data is excluded until the product is solid and Elliot revisits the decision.

Summary of the UK order of evidence:

1. Manufacturer specification or current label for the exact product.
2. Licensed current GTIN data (NIQ Brandbank, GS1 UK productDNA) where a licence exists.
3. Official generic composition (CoFID 2021, OGL v3.0, attribution required), plus official DHSC/Quadram category analyses published after 2021 as overlays that supersede only what they measured.

There is no fourth tier in v1. An item that cannot be matched to one of these sources is reported as a gap, in plain language, with what evidence would close it. Gaps are never filled from weaker data to make coverage look complete.

Hard gates:

- Open-source code does not change data licences. A source with unclear terms is reference-only.
- The Quadram CoFID and Food Labelling APIs are non-commercial; no commercial use without a licence.
- Open Food Facts and other crowd-sourced or community datasets are excluded from the evidence base entirely for now. If they are ever admitted later, the ODbL share-alike duties are assessed before any data moves.
- Brandbank and productDNA are partnership routes, never scrape targets.
- Retailer web pages are not an evidence source in v1. A manufacturer's own published specification is; a retailer's transcription of it is not.

## 7. Scoring: NPM 2004/05

- Scoring basis: per 100 g for food and drink alike, as the guidance requires. Per-100 ml values are converted to per 100 g before scoring, never relabelled: value per 100 g = value per 100 ml ÷ specific gravity, applied only when the caller supplies a gravity (otherwise a 400). The guidance's worked examples 2 and 6 multiply instead; example 3 agrees with division. Reasoning and tests: `docs/API.md`, "Scoring basis".
- Implement the model exactly as specified in the Department of Health technical guidance (January 2011): A points for energy, saturated fat, total sugar and sodium per 100 g; C points for fruit, vegetables and nuts, fibre (NSP where known, otherwise AOAC, each on its own band table) and protein; the protein rule (no protein points at 11+ A points unless fruit, veg and nuts score 5); score = A minus C; food is less healthy at 4+, drink at 1+.
- The implementation must reproduce the guidance's published worked examples before it is used on real products, and boundary fixtures must cover every points band edge.
- NPM 2018 is a shadow requirement from day one, not a roadmap item. DHSC published the NPM 2018 technical guidance on 27 January 2026 (free sugars replacing total sugar, updated bands) and consulted from 25 March to 17 June 2026 on applying it to the advertising and promotions restrictions, with a proposed 12-month implementation period. The outcome was still pending in November 2026. The pack therefore computes both models: 2004/05 as the law in force, 2018 as a shadow score, so a whole range can be rescored the day the outcome lands. Dual scoring ("your range under today's law vs under NPM 2018") is a headline feature.
- The legacy repo's `scoring/hfss.py` must not be reused: it is a self-declared stub that mislabels traffic-light thresholds as HFSS.
- Status: the scorer at `src/shelfscale/npm.py` reproduces all six worked examples in the guidance (section 4, pages 14 to 18), every A point, C point and score, in `tests/test_npm_worked_examples.py`. Band-edge fixtures cover every threshold in the guidance tables, typed independently of the module's constants. Validated November 5, 2026 against the GOV.UK copy of the guidance (sha256 `14ae1fe9…ac71c`, recorded in the test file).
- Traffic lights are NOT implemented in this package. A traffic-light module exists in the legacy codebase on `main` (`shelfscale/scoring/traffic_lights.py`) and is to be ported (build order, section 11). The port is verified line by line against current FSA front-of-pack guidance before it ships, not copied: the legacy per-100 g and per-100 ml thresholds look plausible but are unverified, and its separate per-serving threshold table does not correspond to the FSA's per-portion rule for large portions. Traffic lights keep their own basis (per 100 ml for drinks); the NPM per-100 g rule does not apply to them.
- Nutri-Score exists in the legacy repo and is kept as a future EU-pack asset. It is not the UK NPM.

## 8. Loose item matching (specified method)

1. Normalise the item name and extract attributes: variety, raw or cooked, whole or edible part.
2. Generate candidates from generic composition entries; rerank by rules, fuzzy matching, then model assistance; preparation-state conflicts reject a candidate.
3. Resolve weight: per-kg items scale from per-100 g values; per-item sales use weighed sample means (the 2011 and 2015 fruit and vegetable surveys), then portion tables, then category defaults, with the basis stored.
4. Convert gross to edible weight with edible-portion factors.
5. Compute nutrients and NPM from the matched entry; present per item with its basis and, where sample spread exists, a range rather than false precision.
6. Every loose match is labelled: exact generic match, variety average, or sample-based estimate.

## 9. Updates and the source watch

Update flow (detail in `docs/UPDATE_PIPELINE.md`): watch, snapshot, diff, validate, human review, versioned release. Automation never promotes data. A licence downgrade blocks release.

A monthly source watch is scheduled in Rocky's agent environment (job name there: shelfscale-source-watch-monthly, first run planned for December 1, 2026). It is not part of this repository: its schedule, run history and log live in that environment, and this repository cannot verify that it is running. It is meant to check the registered monthly sources for new editions, new official analysis reports, rule changes and licence changes, and report a short decision brief for human review. It changes no data by itself. Watcher code inside this repository is a later build step (section 11, step 3).

## 10. Validation gates before any release

- Schema, unit and nutrient consistency checks on every import.
- Scorer fixtures, including the NPM worked examples.
- A human-checked match gold set (loose items included) with precision reported per release.
- Licence gate: no release contains data its licence forbids for that use.
- Provenance check: no output ships without data release and pack version.

## 11. Build order (when Elliot gives the go)

1. CoFID importer into canonical observations. (Done November 5, 2026: `src/shelfscale/cofid.py`, lookup in `src/shelfscale/lookup.py`, not yet wired into the HTTP API. Conflicts between the data model and the real files are recorded in `docs/DATA_MODEL.md`.)
2. Portion and sample imports; port of the legacy traffic lights module, verified against FSA guidance. (NPM worked-example validation: done November 5, 2026.)
3. Watcher code and overlay imports (milk, beef, successors).
4. Bulk "score my range" tool and the public API on the dual-model engine (the first user surface the needs research recommends, subject to Elliot's decision in section 12). The API prototype for caller-supplied values already exists; database-backed lookup follows the CoFID importer.
5. Recipe calculator and UK label outputs, portion first.
6. Contribution flow; second country pack via EuroFIR discovery.

Roadmap detail: `docs/ROADMAP.md`.

## 12. Open decisions for Elliot

- First user surface: the needs research recommends the open dual-model NPM engine plus a bulk "score my range" tool (a CSV of products or recipes in; 2004/05 and 2018 scores, HFSS status per UK nation, A/C breakdown and a change report out), ahead of any label-design surface. The decision is Elliot's.
- Whether the open-source project lives in a new public repo or inside the existing Product-nutrition-database repo.
- Whether a hosted or supported version is ever offered commercially. Not assumed in this spec.
- Which licensed data partnerships (Brandbank, productDNA, Nutritics) are worth approaching, and when.
- Rounding before NPM banding. The guidance's worked example 3 reaches its score (0) only by rounding per-100 g values to one decimal before banding; unrounded, the same drink scores 1 and is "less healthy". The guidance states no rounding rule. ShelfScale scores unrounded until this is decided (`tests/test_density.py`).

## 13. API, bulk assessment and image intake (added November 5, 2026)

Elliot directed that the product be usable through an API, that assessment work in bulk rather than one product at a time, and that universities and retailers be designed for from the start. Full contract: `docs/API.md`.

- **Endpoints (prototype live and tested):** `GET /health`, `POST /v1/assess` (one product), `POST /v1/assess/bulk` (a range in one call). Bulk rules: partial success with a per-row error list, a summary block, a 1,000-product synchronous limit, and asynchronous bulk jobs with webhook completion for larger ranges.
- **Scoring basis:** every score is computed per 100 g, food and drink alike. A per-100 ml submission is converted by dividing by the caller's specific gravity and labelled as converted; without a gravity it is a 400.
- **Two modes:** supplied mode (the caller provides the nutrient values; the response states they were not verified by ShelfScale) and lookup mode (ShelfScale resolves values from its own provenance-carrying data; follows the CoFID importer). Every response names the model version and, in lookup mode, the data release.
- **Image intake (specified, staged; full assessment in `docs/IMAGE_ASSESSMENT.md`):** a photograph is an intake method, never evidence. Stage A reads the barcode and resolves the GTIN through the normal evidence order. Stage B OCRs the back-of-pack table into candidate values that a user confirms before they count as a label transcription. Stage C assists loose-item identification only; it cannot settle variety or weight from an image, so it hands over to the section 8 method and its estimate labelling. Each stage ships only after passing a photographed gold-set test.

## 14. Delivery: where the code lives, and what happens if Elliot cannot see it

Elliot raised this on November 5, 2026: code Rocky changed in an earlier project did not appear when he opened GitHub on another machine, because the work only existed in Rocky's own workspace. This section is the standing fix.

**Current status, stated plainly:** delivered to GitHub on November 5, 2026. Repository `elliotkarikari/Product-nutrition-database` (public), branch `shelfscale-open`. Head at handover: `2f44f9c` ("Record GitHub upload attempt and token-scope blocker in delivery section"), on top of `9632df1`. Rocky read the branch back from GitHub and confirmed the tree matches his local copy file for file (22 files); a second read-back the same day confirmed the same head and tree. This branch is canonical for ShelfScale. Its history is self-contained and does not descend from `main`, which holds the legacy LIDA codebase. Whether and when it merges into `main` is Elliot's decision only. The earlier upload blocker (Rocky's token scoped to the agent-vault repository) no longer applies.

**The rule for this project (and the general rule now recorded in the agent vault's Build Rules):**

1. A code change counts as delivered only when it is pushed to the project's GitHub repository and verified by reading the commit back from GitHub. The report to Elliot names the repository, the branch and the commit.
2. Work that exists only in an agent's workspace is reported as local-only, in those words, in the same message that describes the work. Never as "done", "in the repo" or "on GitHub".
3. If a push is not possible or not yet authorised, the agent says so plainly, states exactly where the work sits, and offers the work in a form Elliot can take himself: a patch file, a zip of the project, or paste-ready files, plus the one command or GitHub Desktop step that would publish it.
4. Before reporting any code change, the agent checks: could Elliot open GitHub on another machine right now and see this? If the answer is no, the report leads with that fact and the remedy, not with the change itself.
