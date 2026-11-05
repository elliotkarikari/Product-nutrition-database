---
type: source-register
status: active
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Data source register (UK pack first)

Authority is per question, not per brand: a manufacturer specification beats a generic table for that product, and a generic table beats a crowd-sourced label for a generic food.

| Register id | Source | Gives us | Authority | Licence and commercial use | Watch | Status |
|---|---|---|---|---|---|---|
| `uk-cofid-2021` | CoFID 2021 (GOV.UK spreadsheet) | Generic UK food composition, 2,887 foods (2,886 distinct codes; counted from the 2021 workbook, see `tests/test_cofid.py`) | Highest for generic foods | Open Government Licence v3.0; commercial reuse with attribution | File hash and page change, monthly | Imported: raw snapshot in `data/raw/uk-cofid-2021`, importer `src/shelfscale/cofid.py` |
| `uk-cofid-old-foods` | CoFID old foods file | Foods from the 2008 CoFID not reviewed since (unreviewed set) | Reference for history | OGL v3.0 | With CoFID, monthly | **Deferred, not imported.** Deferred deliberately (2026-11-05): not snapshotted or imported. The CoFID 2021 user guide says these foods were not reviewed or validated in the 2015, 2019 or 2021 updates and their values may not represent the foods as currently consumed. Nothing in the build needs them yet, and importing them would place unreviewed values beside current ones. Revisit when a reported gap needs one; if imported, every observation is marked unreviewed. |
| `uk-dhsc-nutrient-analysis-reports` | DHSC / OHID nutrient analysis reports (pork 2020, milk sampled 2022-23, beef analysed 2024) | New laboratory analyses, category by category | Highest for the foods and nutrients measured | Published on GOV.UK; check each report's terms at ingestion | New publications, monthly | Overlay imports, Phase 2 |
| `uk-quadram-apis` | Quadram FN-NBRI CoFID API and Food Labelling API | Programmatic access to CoFID and labelling data | Official access route | Non-commercial licence (academic, non-profit, education). No commercial ingestion without a licence | Terms and version changes, monthly | Reference only |
| `uk-npm-guidance-2011` | Nutrient Profiling Model technical guidance (DH, January 2011) and the 2021 Promotion and Placement Regulations | The NPM rules and the legal thresholds | Legal authority for scoring | Crown copyright; guidance published for use | Guidance or regulation change, monthly | Implemented in `src/shelfscale/npm.py` |
| `uk-devolved-hfss-guidance` | Scotland Food (Promotion and Placement) Regulations 2025 implementation guidance; Wales and Northern Ireland equivalents | Jurisdiction differences inside the UK | Legal authority per nation | Published guidance; check at ingestion | Monthly | Register in UK pack jurisdiction layer |
| `uk-fsa-labelling-ppds-guidance` | FSA labelling and PPDS (Natasha's Law) guidance | Label and allergen duties | Legal and practical authority | Published guidance | Monthly | Reference for label outputs |
| `uk-dh-fv-sampling-2011` | Nutrient analysis of fruit and vegetables: Sampling Report (DH 2013, sampling 2011-12) | Weighed retail sub-samples and unit weights per fruit and vegetable | Primary survey evidence for weights | OGL v3.0 via GOV.UK site terms (the PDF states only Crown copyright) | Static; re-verify yearly | **Imported**: 12 foods whose tables reproduce the report's stated averages (`src/shelfscale/fv_samples.py`) |
| `uk-phe-fv-sampling-2015` | Fruit and vegetable survey 2015 sampling report (PHE 2017, sampling 2015-16) | Weighed retail sub-samples and unit weights | Primary survey evidence for weights | OGL v3.0, stated in the report | Static; re-verify yearly | **Imported**: 32 foods, same reconciliation rule |
| `uk-food-portion-sizes-2002` | Food Portion Sizes, 3rd edition (FSA 2002, TSO) | Typical portion and pack weights | Primary reference for portions | Crown copyright, sold by TSO; no open licence found | Static; re-verify yearly | **Reference only, not imported**: terms unclear (SPEC 6). Elliot transcribed the legacy table by hand from his own copy; decision on licensing is his |
| `open-food-facts` | Open Food Facts | Branded product data by GTIN | Crowd-sourced; not defensible line by line | ODbL database licence with share-alike on published derived databases; images CC BY-SA | None while excluded | EXCLUDED from the evidence base (Elliot, Nov 5, 2026) until the product is solid and the decision is revisited |
| `niq-brandbank` | NIQ Brandbank content licensing | Current branded FMCG product content at scale | High for covered GTINs | Commercial licence, agreed use cases only | Terms reviewed quarterly; no scraping | Partnership route, not a scrape target |
| `gs1-uk-productdna` | GS1 UK productDNA (Syndigo) | Verified shared product data, HFSS data sharing | High for covered products | Subscription and licence | Quarterly review | Partnership route |
| `nutritics-gb23` | Nutritics GB23 | Commercial enhanced CoFID derivative | Benchmark or possible licence | Commercial; terms by enquiry | Yearly | Benchmark only: compared against, never used as evidence without a licence |
| `eurofir-foodexplorer` | EuroFIR FoodEXplorer | Discovery of national composition datasets for future country packs | Directory, not a dataset | Membership and per-dataset licences | Quarterly | For expansion research |
| `manufacturer-specifications` | Manufacturer and supplier specifications | Exact current values for a product or ingredient | Highest for that item | Supplied by the business or manufacturer for its own products | Event driven | Primary route for customer recipes |
| `usda-fooddata-central` | USDA FoodData Central | US generic and branded reference | Highest for a future US pack | Public domain | Monthly once a US pack starts | Parked until US pack |

The register id column is the `id` in `data/source-register.yaml`. The two must name the same set of sources; `tests/test_source_register.py` enforces it.

## Rules that apply to every row

- No source is ingested before its licence row is filled in.
- A source whose terms are unclear is reference-only: it may inform a human decision, its values do not enter a release.
- Crowd-sourced and retailer-published values are not used at all in v1 (policy, November 2026). An item with no defensible source is reported as a gap, not filled.
