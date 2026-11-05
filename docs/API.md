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
Returns `{"status": "ok", "model": "uk-npm-2004/05"}`.

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
    "fibre_aoac_g": 3.7, "protein_g": 4.8
  }
}
```
`sodium_mg` and `salt_g` are alternatives; supplying both or neither is an error. `is_drink` is optional, defaults to `false`, and must be a JSON boolean; any other value (for example the string `"false"`) is a 400. `fibre_nsp_g` and `fibre_aoac_g` are alternatives in the same way: each is scored on its own band table, and the guidance prefers NSP where it is known. The response names the table used in `fibre_method`.

**Scoring basis.** NPM scores food and drink alike per 100 g. `basis` is optional: `per_100g` (the default) or `per_100ml`. A `per_100ml` request must carry `specific_gravity` in g/ml; without it the request is a 400, because per-100 ml values cannot be scored or converted honestly without the product's density. `specific_gravity` on a `per_100g` request is also a 400. With both, every amount-based input (energy, saturated fat, sugars, sodium or salt, fibre, protein) is converted as **value per 100 g = value per 100 ml ÷ specific gravity**, and the response's `input_conversion` block shows the gravity, the rule and each value before and after. `fruit_veg_nuts_percent` is a share, not an amount, and passes through unchanged. A `per_100g` request returns `input_conversion: null`.

**Why ShelfScale divides where the guidance multiplies.** 100 ml of a product with specific gravity G weighs 100·G grams, so a nutrient amount per 100 g is the amount per 100 ml divided by G. The DH guidance (January 2011) is inconsistent on this:

- Worked example 3 (powdered milkshake) converts 200 ml of milk to grams by multiplying by the gravity: 200 ml × 1.034 = 206.8 g. That is volume times density, which is correct. (The guidance prints the gravity as "0.034"; its own 206.8 g shows it means 1.034.) Dividing per-100 ml values by 1.034 reproduces the example's per-100 g milk figures exactly (`tests/test_density.py`).
- Worked examples 2 (ice cream, gravity 0.55) and 6 (juice drink, gravity 1.04) multiply per-100 ml nutrient values by the gravity to get per-100 g values. That inverts the conversion. In example 2 the per-100 g column comes straight from McCance and Widdowson, so the score is right but the method shown is not; in example 6 the score is the same either way (2) but the per-100 g values differ (170.2 kJ by division against the guidance's 184 kJ).

The code follows physics, and example 3, because a method that moves values in the wrong direction will eventually move a product across a band edge. This is a recorded decision; if Elliot rules the other way, the change is one line in `service.py` plus these tests.

**Rounding before banding (open, SPEC section 12).** Worked example 3 only scores 0 because its mixed per-100 g values are rounded to one decimal before banding: unrounded, saturated fat is 1.037 g (over the 1 g edge) and the drink scores 1, "less healthy". The guidance never states a rounding rule. ShelfScale scores values exactly as supplied or converted, unrounded, until Elliot decides.

Response: the NPM score, A and C point breakdowns, `less_healthy` against the food (4+) or drink (1+) threshold, the model id, the basis (always `per_100g`), an optional `per_portion` view when `portion_g` is given, and an evidence note stating the values were caller-supplied and not verified by ShelfScale.

**Traffic lights.** Every assessment also carries `traffic_lights`, the UK front-of-pack colours for fat, saturates, sugars and salt, implemented from the DH/FSA *Guide to creating a front of pack (FoP) nutrition label* (updated November 2016), Annex 3 (`src/shelfscale/traffic_lights.py`):

- Food is coloured per 100 g, whether or not it is sold by volume. Drinks are coloured per 100 ml, so drink colours need per-100 ml values: a drink submitted with `basis: "per_100ml"` (and its `specific_gravity`) is coloured; a drink submitted per 100 g gets `colours: null` and a `not_assessed` reason. ShelfScale does not assume a density to fill the gap.
- Red-only per-portion cut-offs apply when the portion is more than 100 g (food, from `portion_g`) or more than 150 ml (drink, from `portion_ml`, drinks only). They override the per-100 colour; each nutrient says which rule decided it (`decided_by`).
- Total fat is not an NPM input, so it is the optional `nutrients.fat_g`. Without it, fat is reported as not assessed; the other three are still coloured. Salt comes from `salt_g`, or from `sodium_mg` / 400.
- Energy is not colour coded, and there is no overall colour: the guidance defines neither.

### POST /v1/assess/bulk
Assess a range in one call: `{"products": [ ... ]}` with the single-product shape per item.

Rules that matter to bulk users:

- **Partial success.** A bad row lands in `errors` with its index, id and reason. It never blocks the rest of the range.
- **Summary first.** The response carries counts: received, assessed, failed, less_healthy.
- **Synchronous limit: 1,000 products per call.** Larger ranges use the asynchronous bulk job below.
- Every result names the model version, so a range scored today can be compared honestly with the same range scored after a model or data change.

### Asynchronous bulk jobs (specified, for ranges above the sync limit)
- `POST /v1/bulk-jobs` accepts a file or a product list plus an optional webhook URL and an idempotency key, and returns a job id immediately.
- On completion the API calls the webhook with the result location. A status endpoint exists for systems that cannot receive webhooks; clients should prefer the webhook over polling.
- Results are delivered as a downloadable file (JSON and CSV) plus the same summary block as the synchronous endpoint.
- Re-running the same idempotency key returns the original job instead of scoring twice.

## Two modes of assessment

1. **Supplied mode (live in the prototype).** The caller provides nutrient values; ShelfScale scores them and says plainly that it has not verified them. This is the mode a university teaching lab or a brand scoring its own specification data uses.
2. **Lookup mode (follows the CoFID importer).** The caller provides a GTIN, a product name or a recipe; ShelfScale resolves values from its own provenance-carrying data and returns the observations and sources behind the score. A score in lookup mode always names its data release.

## Production requirements before public hosting

- API keys per organisation, with per-key rate limits and usage metering.
- TLS, request size limits, and audit logs that record model and data-release versions per call.
- Versioned base path (`/v1`) and a published deprecation policy.
- For lookup mode: responses cacheable by data release, so a retailer's nightly range check only re-scores what a new release changed.
- No caller data retained beyond the job unless the organisation opts in.

## Who this serves

- **Universities:** teaching and research scoring with a citable model version; bulk scoring of survey or retail datasets; reproducible results because the model and data release are named in every response.
- **Retailers and wholesalers:** nightly or weekly range classification, change reports between releases, and a clean error list of products whose data is missing or unusable, which is the list their suppliers need to fix.
- **Brands and manufacturers:** scoring their own specification data before a retailer asks, including the NPM 2018 shadow score once that model is implemented.
