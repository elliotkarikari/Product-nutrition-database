---
type: api-contract
status: prototype-live
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# ShelfScale API

The API is how universities, retailers, brands and builders use ShelfScale without the (future) web interface. Bulk assessment is a first-class citizen, not an afterthought: the main users score ranges, not single products.

## Prototype status

Working prototype, standard library only, in `src/shelfscale/api.py` with the scoring service in `src/shelfscale/service.py`. Covered by tests, including a live HTTP test of both POST endpoints.

Run locally:

```
PYTHONPATH=src python3 -m shelfscale.api --port 8765
```

## Endpoints (v1)

### GET /health
Returns `{"status": "ok", "models": {"uk-npm-2004/05": "in force", "uk-npm-2018": "shadow model, not in force"}}`.

## Two models in every result

Every assessment and lookup result is scored under two models, side by side:

- `uk-npm-2004/05`: the model in force (DH technical guidance, January 2011). `status: "in force"`.
- `uk-npm-2018`: the 2018 model from DHSC's technical guidance, published 27 January 2026. `status: "shadow model, not in force"`. It is not the law; it is shown so a range can be checked against the model the government has consulted on. Rules and sources: `src/shelfscale/npm2018.py`, validated against all 17 of DHSC's worked examples (`tests/test_npm2018.py`).

Each result carries `models`, keyed by model id. Each block has `model`, `status`, `scorable`, and either `score`, `less_healthy`, `a_points`, `c_points`, `total_a`, `total_c`, `protein_counted` and (2004/05 only) `fibre_method`, or `missing_inputs` naming what is missing. The 2018 block also has `inputs`, saying where each 2018 input came from. `verdict_changes_under_2018` is `true` or `false` when both models scored, and `null` when either could not. (This replaces the earlier single-model top-level `score`, `less_healthy` and points fields; there is no compatibility copy.)

What the 2018 model needs, and how ShelfScale gets it:

- **Free sugars, never total sugars (decided by Elliot, November 5, 2026).** 2018 scores free sugars. Only the caller can supply them, as `free_sugars_g` (labelled `caller_supplied`). Without it the 2018 block is `scorable: false` with free sugars named as missing. Total sugars are never substituted, and no "indicative" 2018 score is produced from them.
- **Salt, not sodium.** From `salt_g`, or from `sodium_mg` / 400 (salt = sodium × 2.5), and the input says which.
- **AOAC fibre only.** The guidance says to convert NSP "using an appropriate conversion factor" but gives none, so NSP-only input leaves 2018 unscored, with the reason given.
- **Fruit, vegetables, nuts and seeds** (`fvns_g`, g per 100 g). Seeds count under 2018. Without `fvns_g`, `fruit_veg_nuts_percent` is used and labelled as the 2004/05 definition, which does not count seeds.
- **Foods and non-alcoholic drinks only.** Alcoholic drinks get `applicable: false`.
- **Volume conversion.** Same rule as 2004/05: per 100 ml ÷ specific gravity. The 2018 guidance's prose says to multiply, but its own worked examples 1, 2, 3, 5 and 17 divide; ShelfScale follows the examples.

### POST /v1/assess
Assess one product from caller-supplied per-100 g nutrient values. Food and drink alike are scored per 100 g, as the NPM guidance requires.

Request:
```json
{
  "id": "beans-400g",
  "is_drink": false,
  "portion_g": 200,
  "nutrients": {
    "energy_kj": 340, "saturated_fat_g": 0.1, "total_sugars_g": 5,
    "sodium_mg": 250, "fruit_veg_nuts_percent": 50,
    "fibre_aoac_g": 3.7, "protein_g": 4.8,
    "free_sugars_g": 0.5, "fvns_g": 50
  }
}
```
`free_sugars_g` and `fvns_g` are optional and used only by the 2018 shadow model.
`sodium_mg` and `salt_g` are alternatives; supplying both or neither is an error. `is_drink` is optional, defaults to `false`, and must be a JSON boolean; any other value (for example the string `"false"`) is a 400. `fibre_nsp_g` and `fibre_aoac_g` are alternatives in the same way: each is scored on its own band table, and the guidance prefers NSP where it is known. The response names the table used in `fibre_method`.

**Scoring basis.** NPM scores food and drink alike per 100 g. `basis` is optional: `per_100g` (the default) or `per_100ml`. A `per_100ml` request must carry `specific_gravity` in g/ml; without it the request is a 400, because per-100 ml values cannot be scored or converted honestly without the product's density. `specific_gravity` on a `per_100g` request is also a 400. With both, every amount-based input (energy, saturated fat, sugars, sodium or salt, fibre, protein) is converted as **value per 100 g = value per 100 ml ÷ specific gravity**, and the response's `input_conversion` block shows the gravity, the rule and each value before and after. `fruit_veg_nuts_percent` is a share, not an amount, and passes through unchanged. Free sugars are converted the same way; `fvns_g`, like FVN, is a share and passes through unchanged. A `per_100g` request returns `input_conversion: null`.

**Why ShelfScale divides where the guidance multiplies.** 100 ml of a product with specific gravity G weighs 100·G grams, so a nutrient amount per 100 g is the amount per 100 ml divided by G. The DH guidance (January 2011) is inconsistent on this:

- Worked example 3 (powdered milkshake) converts 200 ml of milk to grams by multiplying by the gravity: 200 ml × 1.034 = 206.8 g. That is volume times density, which is correct. (The guidance prints the gravity as "0.034"; its own 206.8 g shows it means 1.034.) Dividing per-100 ml values by 1.034 reproduces the example's per-100 g milk figures exactly (`tests/test_density.py`).
- Worked examples 2 (ice cream, gravity 0.55) and 6 (juice drink, gravity 1.04) multiply per-100 ml nutrient values by the gravity to get per-100 g values. That inverts the conversion. In example 2 the per-100 g column comes straight from McCance and Widdowson, so the score is right but the method shown is not; in example 6 the score is the same either way (2) but the per-100 g values differ (170.2 kJ by division against the guidance's 184 kJ).

The code follows physics, and example 3, because a method that moves values in the wrong direction will eventually move a product across a band edge. This is a recorded decision; if Elliot rules the other way, the change is one line in `service.py` plus these tests.

**Never round before banding (standing rule, Elliot, November 5, 2026).** NPM points are banded on values exactly as supplied, looked up or converted. The recorded reason: worked example 3 only scores 0 because its mixed per-100 g values are rounded to one decimal before banding; unrounded, saturated fat is 1.037 g (over the 1 g edge) and the drink scores 1, "less healthy". The guidance never states a rounding rule, so none is applied.

Response: `models` (both NPM results, each with its score, A and C points and `less_healthy` against the food (4+) or drink (1+) threshold), `verdict_changes_under_2018`, the basis (always `per_100g`), an optional `per_portion` view when `portion_g` is given, and an evidence note stating the values were caller-supplied and not verified by ShelfScale.

**Traffic lights.** Every assessment also carries `traffic_lights`, the UK front-of-pack colours for fat, saturates, sugars and salt, implemented from the DH/FSA *Guide to creating a front of pack (FoP) nutrition label* (updated November 2016), Annex 3 (`src/shelfscale/traffic_lights.py`):

- Food is coloured per 100 g, whether or not it is sold by volume. Drinks are coloured per 100 ml, so drink colours need per-100 ml values: a drink submitted with `basis: "per_100ml"` (and its `specific_gravity`) is coloured; a drink submitted per 100 g gets `colours: null` and a `not_assessed` reason. ShelfScale does not assume a density to fill the gap.
- Red-only per-portion cut-offs apply when the portion is more than 100 g (food, from `portion_g`) or more than 150 ml (drink, from `portion_ml`, drinks only). They override the per-100 colour; each nutrient says which rule decided it (`decided_by`).
- Total fat is not an NPM input, so it is the optional `nutrients.fat_g`. Without it, fat is reported as not assessed; the other three are still coloured. Salt comes from `salt_g`, or from `sodium_mg` / 400.
- Energy is not colour coded, and there is no overall colour: the guidance defines neither.

### POST /v1/assess/bulk
Assess a range in one call: `{"products": [ ... ]}` with the single-product shape per item.

Rules that matter to bulk users:

- **Partial success.** A bad row lands in `errors` with its index, id and reason. It never blocks the rest of the range.
- **Summary first.** The response carries counts: received, assessed, failed; `scorable` and `less_healthy` per model id; and `verdict_changes_under_2018`, the number of products whose verdict differs between the two models.
- **Synchronous limit: 1,000 products per call.** Split larger ranges into multiple calls; asynchronous bulk jobs below are not implemented.
- Every result names the model version, so a range scored today can be compared honestly with the same range scored after a model or data change.

### POST /v1/lookup
Look up one CoFID 2021 food and, where it is scorable, assess it. Lookup is its own endpoint rather than a mode of `/v1/assess`, because the request shape is different (a food reference, not nutrient values).

Request: `{"code": "13-669"}` or `{"name": "Milk, whole, pasteurised, average"}` (exactly one; the name must match exactly), plus optional `fvn_percent` (0-100), `portion_g`, `free_sugars_g` and `fvns_g` (both 0-100, g per 100 g of the food).

Response: the query, the CoFID release (source, edition, file URL, retrieval date, sha256, licence, attribution), a `note`, and `matches`: every food with that code or name. Codes and names are not unique in CoFID 2021 (13-669 is two foods), so this is always a list; no match is a gap and is said to be one. Each match carries all its observations with provenance (source, edition, food code, table, nutrient code and label, unit, basis, method, value text) and an `assessment`:

- `inputs` says where every assessment input came from: the CoFID nutrient code and its value, "trace counted as 0", `derived_from_group`, or `caller_supplied`.
- Energy KJ, saturated fat SATFOD, total sugars TOTSUG, sodium NA, protein PROT, fat FAT (traffic lights only). Fibre is NSP (ENGFIB) where CoFID gives a value, otherwise AOAC (AOACFIB); `fibre_method` names it.
- **Fruit, vegetables and nuts (decided by Elliot, November 5, 2026).** CoFID has no FVN percentage. A caller-supplied `fvn_percent` always wins (`caller_supplied`). Otherwise: potatoes (CoFID groups DA*) carry 0%, labelled `excluded_by_guidance`, because the NPM guidance says potatoes do not count; vegetable dishes (DR) are composite and not yet scorable; any other food in group D (vegetables), F (fruit) or G (nuts and seeds) carries 100%, labelled `derived_from_group`; every other food is not yet scorable. FVN is never estimated from the food's name. Groups DB, DF, DG, DI, FC, GA and FA keep the 100% rule and are flagged for review: GA includes seeds and FA includes sugared and syrup fruit, which the guidance would not count in full.
- Drink status comes from the CoFID group: P (beverages), Q (alcoholic), BH (milk-based drinks), FC (fruit juices). The response says which group decided it.
- Alcoholic drinks (Q) are per 100 ml in CoFID; they are converted to per 100 g by the food's own CoFID specific gravity, and are not scorable without one. Other drinks have no per-100 ml values in CoFID, so their traffic lights are not assessed.
- Each model block is either `scorable: false` with `missing_inputs` named, or scored. When 2004/05 is scorable the assessment adds the same traffic-light block as `/v1/assess`.
- **NPM 2018 in lookup.** CoFID records total sugars, not free sugars, so a CoFID food is not scorable under 2018 unless the caller supplies `free_sugars_g`; the block carries a `free_sugars_note` saying so. Fibre is AOAC (AOACFIB) only. Fruit, vegetables, nuts and seeds follow the same group rule as FVN, or the caller's `fvns_g`. Alcoholic drinks (Q) are outside the 2018 model.
- Example of a verdict change: 14-834 *Peanuts, roasted and salted*, with `free_sugars_g: 0`, scores 5 (less healthy) under 2004/05 and 1 (not less healthy) under 2018, mainly because AOAC fibre (8.0 g) earns 10 points on the 2018 scale where NSP fibre (6.0 g) earned 5.

### POST /v1/lookup/bulk
`{"items": [ ... ]}`, each item shaped like a `/v1/lookup` request. Same rules as `/v1/assess/bulk`: partial success, per-row `errors` with index and reason, a 1,000-item synchronous limit. The summary counts received, looked up, failed, no match and foods matched, plus `scorable` and `less_healthy` per model and `verdict_changes_under_2018`.

### Asynchronous bulk jobs (specified only; not implemented)
- `POST /v1/bulk-jobs` accepts a file or a product list plus an optional webhook URL and an idempotency key, and returns a job id immediately.
- On completion the API calls the webhook with the result location. A status endpoint exists for systems that cannot receive webhooks; clients should prefer the webhook over polling.
- Results are delivered as a downloadable file (JSON and CSV) plus the same summary block as the synchronous endpoint.
- Re-running the same idempotency key returns the original job instead of scoring twice.

## Two modes of assessment

1. **Supplied mode (live in the prototype).** The caller provides nutrient values; ShelfScale scores them and says plainly that it has not verified them. This is the mode a university teaching lab or a brand scoring its own specification data uses.
2. **Lookup mode (live for CoFID 2021 foods: `/v1/lookup`).** The caller names a CoFID food by code or exact name; ShelfScale returns its observations with provenance and the data release, and scores it where every input can be sourced. GTIN, product-name and recipe lookup come later.

## Remaining production requirements (prototype is already publicly hosted)

- API keys per organisation, with per-key rate limits and usage metering.
- TLS, request size limits, and audit logs that record model and data-release versions per call.
- Versioned base path (`/v1`) and a published deprecation policy.
- For lookup mode: responses cacheable by data release, so a retailer's nightly range check only re-scores what a new release changed.
- No caller data retained beyond the job unless the organisation opts in.

## Who this serves

- **Universities:** teaching and research scoring with a citable model version; bulk scoring of survey or retail datasets; reproducible results because the model and data release are named in every response.
- **Retailers and wholesalers:** nightly or weekly range classification, change reports between releases, and a clean error list of products whose data is missing or unusable, which is the list their suppliers need to fix.
- **Brands and manufacturers:** scoring their own specification data before a retailer asks, including the NPM 2018 shadow score (needs their free sugars figure).

Numeric inputs must be finite and non-negative; portions and density must be positive. Non-finite JSON constants, invalid body framing and invalid UTF-8 are rejected. Request bodies are limited to 5,000,000 bytes and a 10-second socket timeout. IDs/names in supplied mode must be nonempty strings.
