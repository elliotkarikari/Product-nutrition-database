---
type: source-register
status: active
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Data source register (UK pack first)

Authority is per question, not per brand: a manufacturer specification beats a generic table for that product, and a generic table beats a crowd-sourced label for a generic food.

| Source | Gives us | Authority | Licence and commercial use | Watch | Status |
|---|---|---|---|---|---|
| CoFID 2021 (GOV.UK spreadsheet) | Generic UK food composition, 2,898 foods | Highest for generic foods | Open Government Licence v3.0; commercial reuse with attribution | File hash and page change, monthly | Importer is Phase 1 |
| CoFID old foods file | Legacy and superseded entries | Reference for history | OGL v3.0 | With CoFID, monthly | Reference |
| DHSC / OHID nutrient analysis reports (pork 2020, milk sampled 2022-23, beef analysed 2024) | New laboratory analyses, category by category | Highest for the foods and nutrients measured | Published on GOV.UK; check each report's terms at ingestion | New publications, monthly | Overlay imports, Phase 2 |
| Quadram FN-NBRI CoFID API and Food Labelling API | Programmatic access to CoFID and labelling data | Official access route | Non-commercial licence (academic, non-profit, education). No commercial ingestion without a licence | Terms and version changes, monthly | Reference only |
| Nutrient Profiling Model technical guidance (DH, January 2011) and the 2021 Promotion and Placement Regulations | The NPM rules and the legal thresholds | Legal authority for scoring | Crown copyright; guidance published for use | Guidance or regulation change, monthly | Implemented in `src/shelfscale/npm.py` |
| Scotland Food (Promotion and Placement) Regulations 2025 implementation guidance; Wales and Northern Ireland equivalents | Jurisdiction differences inside the UK | Legal authority per nation | Published guidance; check at ingestion | Monthly | Register in UK pack jurisdiction layer |
| FSA labelling and PPDS (Natasha's Law) guidance | Label and allergen duties | Legal and practical authority | Published guidance | Monthly | Reference for label outputs |
| Legacy ShelfScale datasets: Food Portion Sizes, fruit and vegetable sample reports 2011 and 2015 | Portion sizes and weighed loose-item samples | Primary survey evidence for weights | Government survey data held in Elliot's research repo; verify redistribution terms before publishing values | Static; re-verify yearly | Import as portion observations, Phase 1 |
| Open Food Facts | Branded product data by GTIN | Crowd-sourced; not defensible line by line | ODbL database licence with share-alike on published derived databases; images CC BY-SA | None while excluded | EXCLUDED from the evidence base (Elliot, Nov 5, 2026) until the product is solid and the decision is revisited |
| NIQ Brandbank content licensing | Current branded FMCG product content at scale | High for covered GTINs | Commercial licence, agreed use cases only | Terms reviewed quarterly; no scraping | Partnership route, not a scrape target |
| GS1 UK productDNA (Syndigo) | Verified shared product data, HFSS data sharing | High for covered products | Subscription and licence | Quarterly review | Partnership route |
| Nutritics GB23 | Commercial enhanced CoFID derivative | Benchmark or possible licence | Commercial; terms by enquiry | Yearly | Enquiry only |
| EuroFIR FoodEXplorer | Discovery of national composition datasets for future country packs | Directory, not a dataset | Membership and per-dataset licences | Quarterly | For expansion research |
| Manufacturer and supplier specifications | Exact current values for a product or ingredient | Highest for that item | Supplied by the business or manufacturer for its own products | Event driven | Primary route for customer recipes |
| USDA FoodData Central | US generic and branded reference | Highest for a future US pack | Public domain | Monthly once a US pack starts | Parked until US pack |

## Rules that apply to every row

- No source is ingested before its licence row is filled in.
- A source whose terms are unclear is reference-only: it may inform a human decision, its values do not enter a release.
- Crowd-sourced and retailer-published values are not used at all in v1 (policy, November 2026). An item with no defensible source is reported as a gap, not filled.
