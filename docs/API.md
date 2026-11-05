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
`sodium_mg` and `salt_g` are alternatives; supplying both or neither is an error. `fibre_nsp_g` and `fibre_aoac_g` are alternatives in the same way: each is scored on its own band table, and the guidance prefers NSP where it is known. The response names the table used in `fibre_method`.

**Scoring basis.** `basis` is optional and the only accepted value is `per_100g`. A request with `basis: "per_100ml"` (or any other value) is rejected with a 400 that asks the caller to convert first. ShelfScale never relabels per-100 ml values as per-100 g. Converting per 100 ml to per 100 g needs the product's density; this is not built yet because the guidance's worked examples 2 and 6 multiply per-100 ml values by specific gravity, whereas dividing is the physically correct conversion. That conflict is for Elliot to resolve before any conversion ships.

Response: the NPM score, A and C point breakdowns, `less_healthy` against the food (4+) or drink (1+) threshold, the model id, the basis (always `per_100g`), an optional `per_portion` view when `portion_g` is given, and an evidence note stating the values were caller-supplied and not verified by ShelfScale.

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
