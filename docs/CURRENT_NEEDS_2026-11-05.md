---
type: research-report
status: final
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# ShelfScale: current UK need — decision-ready research report

Researched 2026-11-05. Focus: 2025–2026 evidence. Verified facts and inference are separated throughout.

## Bottom line

The need is real, current, and unusually time-specific. Three separate scoring/labelling waves are landing inside 24 months: England volume-promotion rules (in force 1 Oct 2025), UK-wide advertising restrictions (in force 5 Jan 2026), Wales promotion/placement rules (in force 26 Mar 2026), Scotland's rules (in force 1 Oct 2026), plus a live government proposal to swap the underlying scoring model itself (NPM 2018), which would force every affected product to be rescored. The pain is documented by the trade bodies themselves: there is still **no standardised NPM calculator**, and classification data does not flow cleanly through the supply chain. The gap is not "nutrition software" in general — Nutritics, NutriCalc, Kafoodle and Brandbank serve that — it is a free, auditable, provenance-carrying scoring and data layer underneath them.

## 1. Who needs this, ranked by urgency × ability to pay

| Rank | Segment | Urgency | Ability to pay | Why |
|---|---|---|---|---|
| 1 | **Food/drink manufacturers and brands in HFSS categories** (confectionery, cereals, soft drinks, snacks, ready meals, bakery) supplying retail, incl. SMEs | **Highest, now** | **Highest, proven** | Their products are scored for placement, promotions and (since Jan 2026) advertising eligibility. Retailers demand the data from them; a wrong score costs listings and promo slots. Scotland's 1 Oct 2026 start and a possible NPM 2018 switch multiply the work. FDF Scotland is giving SMEs up to £5,000 for reformulation support, including "recipe development software and specialist consultancy" (see §4). |
| 2 | **Retailers, wholesalers and symbol groups (50+ employees)** — the legally obligated parties for promotion/placement | High, now | High, but mostly already served | They must classify entire ranges and push eligibility into EPOS/promotion systems. The ACS (50,000+ convenience stores) told the NPM 2018 consultation that retailers "rely on data provided through multiple wholesalers and suppliers, and the absence of a standardised NPM calculator… increases the risk of inconsistent interpretation and duplication of effort." Large chains buy Brandbank/productDNA; the independent/symbol long tail is underserved. |
| 3 | **Small producers selling prepacked food** (farm shops, market producers moving online/D2C, small brands) | Steady, rising | Low–medium, price-sensitive | Prepacked food needs a full nutrition declaration; calculated (database) analysis is legally permitted and is what most use instead of £150–400/product lab tests. Volume of businesses is large; willingness to pay is real but capped around £20–100/month (see §4). |
| 4 | **Bakeries, delis, sandwich shops — PPDS sellers** | High since 2021, chronic | Low | Natasha's Law applies with **no small-business exemption**. But note the limit: PPDS labels legally require name + full ingredients with allergens emphasised — **nutrition declaration is NOT required on PPDS**. Their buyable pain is ingredient ordering/allergen derivation from recipes, not NPM. Do not sell them nutrition scoring as a legal need. |
| 5 | **Public-sector menu teams: school caterers, NHS and care catering** | Deadline-driven (Sept 2027) | Medium, via contracts/procurement | Updated England School Food Standards were consulted on Apr–Jun 2026 and come into force **September 2027**; the DfE/DHSC feasibility pilot (autumn 2025, 11 schools) found caterers doing menu nutrient analysis and asking for ~12 months' lead-in. Nutritics/Kafoodle hold much of this segment already. Separately, the 10 Year Health Plan commits to **mandatory healthy food sales reporting for large food businesses**, with NPM as the candidate metric — consultation still pending as of late 2026. |
| 6 | **Researchers and app builders** | Steady | Low direct, high strategic | They need the open dataset/API itself (CoFID in usable form, scores, provenance). This is the open-source distribution engine, not the revenue base. |

## 2. Regulatory and operational triggers — verified status

- **Advertising restrictions, UK-wide, IN FORCE 5 Jan 2026.** 9pm TV watershed + total ban on paid online ads for "less healthy" products (13 categories + NPM 2004/05 score ≥4 food / ≥1 drink). ASA already enforcing. Source: DHSC guidance, gov.uk — https://www.gov.uk/government/publications/restricting-advertising-of-less-healthy-food-or-drink-on-tv-and-online-products-in-scope/restricting-advertising-of-less-healthy-food-or-drink-on-tv-and-online-products-in-scope
- **England promotion/placement:** placement rules since Oct 2022; **volume-price (multibuy) restrictions in force 1 Oct 2025**; free-refill ban for HFSS drinks in out-of-home (50+ employees). Food (Promotion and Placement) (England) Regulations 2021.
- **Wales:** Food (Promotion and Presentation) (Wales) Regulations 2025, **in force 26 Mar 2026** — placement + volume promotions + free refills. Source: Welsh Government Healthy Weight delivery plan 2025–2027 — https://www.gov.wales/healthy-weight-healthy-wales-delivery-plan-2025-2027-html
- **Scotland:** Food (Promotion and Placement) (Scotland) Regulations 2025, **in force 1 Oct 2026** — placement (stores >2,000 sq ft) + multibuys + free refills; meal deals and temporary price reductions were removed from scope in June 2025. Implementation guidance published 17 Mar 2026 — https://www.gov.scot/publications/food-promotion-placement-scotland-regulations-2025-implementation-guidance/ The guidance names McCance & Widdowson/CoFID as the "generally established and accepted data" for calculating NPM.
- **Northern Ireland:** no promotion restrictions yet. FSA/Department of Health consultation ran **29 Jul – 21 Oct 2026** on introducing them. Source: NI consultation document — https://www.health-ni.gov.uk/sites/default/files/2026-07/doh-hfss-promotion-consultation-doc.pdf
- **THE MODEL ITSELF MAY CHANGE — the single biggest near-term trigger.** DHSC published the **NPM 2018** technical guidance on **27 Jan 2026** (free sugars replacing total sugar, updated fibre/salt/energy bands) and consulted 25 Mar – 17 Jun 2026 on applying it to the advertising and promotions restrictions, with a proposed 12-month implementation period. Outcome not yet published as of this report. Every in-scope product would need rescoring; more free-sugar products (some yoghurts, cereal bars) come into scope. Sources: DHSC consultation — https://www.gov.uk/government/consultations/applying-the-new-npm-to-advertising-and-promotions-restrictions/applying-the-new-npm-to-advertising-and-promotions-restrictions ; Parliamentary answer, 9 Jul 2026 — https://questions-statements.parliament.uk/written-questions/detail/2026-07-06/16136
- **PPDS / Natasha's Law:** in force UK-wide since 1 Oct 2021, no size exemption; FSA allergen guidance updated 17 Jul 2026. Nutrition declaration not required on PPDS itself.
- **Nutrition labelling (prepacked):** unchanged baseline law, but it is the gateway obligation that pushes small producers from spreadsheets to software the moment they sell beyond the counter (online, wholesale, retail).
- **School food:** updated standards in force **Sept 2027** (England); pilot findings and example menus with nutrient analysis published by DfE/DHSC, Oct 2026 — https://www.gov.uk/government/publications/updating-the-school-food-standards-feasibility-pilot-findings/updating-the-school-food-standards-feasibility-pilot-findings-summary
- **Online product data quality (supporting evidence of pain):** FSA Retail Surveillance Sampling (Jun–Dec 2024, published Jul 2025): of 822 physical and online retail samples, 4% of allergen-tested samples had undeclared allergens; bread products had the worst compliance, mainly labelling issues. University of Nottingham research found 36% of sampled imported products carried pack-to-online allergen information inconsistencies. Sources: https://www.foodsafetynews.com/2025/07/sampling-uncovers-allergen-and-authenticity-issues/ ; https://eprints.nottingham.ac.uk/81914/

## 3. What people do now, and where it hurts

- **Brands/retailers:** Brandbank (NIQ) and GS1 UK productDNA for GTIN-level data; Brandbank already sells supplier-provided NPM scores **and** "Trading Standards-assured" estimated scores where suppliers don't provide data. In-house nutrition/regulatory teams at the top end. Pain (ACS submission, Jun 2026): classifications arrive late and inconsistently from multiple suppliers; every NPM change means EPOS, pricing and promo-system reconfiguration; no standard calculator means duplicated, divergent scoring.
- **SME manufacturers:** spreadsheets, retailer-by-retailer data requests, consultants, and grant-funded help (FDF Scotland's free NPM calculation/reformulation support exists precisely because SMEs can't do this alone).
- **Small producers/caterers:** Nutritics (from ~$21/user/month per Capterra/GetApp listings, 2026), NutriCalc (£75–150/user/month published tiers), Kafoodle (from £20/feature/month listings; £100+/month in practice for multi-site), ReciPal (US-shaped, $19–129/month), plus a new 2026 entrant tier of UK kitchen tools at £25–65/month. Lab analysis at roughly £169–243 per product per test (UK lab list prices) anchors the "calculation beats testing" economics.
- **Public sector:** Nutritics/Kafoodle inside catering contracts; the school pilot shows menu nutrient analysis done by caterers with generic (CoFID) data plus judgement calls for processed foods — exactly the provenance problem.

**Gaps an open-source, provenance-first, portion-first product can credibly fill:**

1. **A standard, inspectable NPM calculator** — both models (2004/05 live law, 2018 shadow), validated on the DHSC worked examples, showing A/C points. Trade bodies are on record asking for this; incumbents' calculators are black boxes tied to subscriptions.
2. **Dual scoring as a feature:** "your range under today's law vs under NPM 2018" — the rescore-everything moment is a once-a-decade data event and nobody's spreadsheet survives it.
3. **Provenance per value** (source dataset, edition, analysis year, manufacturer vs generic vs estimate) — Brandbank's estimated scores and Nutritics' gap-filled GB23 both blur this; Scotland's guidance makes evidence-of-basis an enforcement conversation.
4. **Loose and own-made items** — no GTIN, no label: outside Brandbank's model, inside nobody's calculator. Sample-weight + composite matching is genuinely unoccupied.
5. **Portion-first outputs** — per item/portion as eaten alongside per-100g compliance values; incumbents lead with per-100g.

## 4. Willingness to pay — verified vs inference

**Verified prices/facts:**

- ReciPal (own pricing pages, verified Nov 2026): $29/recipe pay-as-you-go; Business $59/mo ($49 annual); Business Plus $129/mo ($107 annual); Personal $19/mo ($15 annual).
- NutriCalc published tiers: £75/mo Professional, £100/mo Plus, £150/mo Premium per user (via 2026 comparison/guide listings of its pricing).
- Nutritics: from ~$21 per user/month starting price (Capterra/GetApp, updated Oct 2026); real food-business deployments price higher.
- Kafoodle: from £20/feature/month (directory listings); multi-site contracts £100+/month.
- UK lab nutrition analysis: ~£169 ex VAT per test, ~£243 for a labelling package (Foodtest list prices, 2026).
- **FDF Scotland Reformulation for Health**: grants up to **£5,000 per Scottish SME manufacturer**, explicitly usable for nutritional analysis, recipe software and consultancy; applications closed 31 May 2026 for the Oct 2026 regulations round — direct evidence of public money underwriting exactly this spend. https://scottishbusinessnews.net/fdf-scotland-backs-healthier-food-push-with-new-sme-reformulation-fund/
- ACS-estimated retailer compliance costs (£13k small shops, up to £100k larger stores, mostly layout/systems) — trade-body estimate, treat as indicative.

**Inference (labelled as such):** that a £10–30/month hosted tier or paid support/API plan can convert a fraction of the spreadsheet segment; that wholesalers/symbol groups would pay for a classification feed for independents. No verified revenue figures exist for any competitor; do not quote market size.

## 5. First product slice — relevant now, and deliberately not more

**Build first (UK pack only):**

1. **Open NPM engine**: faithful 2004/05 implementation proven against the DHSC 2011 worked examples, with NPM 2018 implemented alongside as a shadow score from day one (a build requirement, not a roadmap item — the consultation outcome could land any month).
2. **"Score my range" bulk tool**: CSV of products/recipes in → NPM 2004/05 and 2018 scores, HFSS status per nation (England/Wales/Scotland rules differ in scope and dates), A/C point breakdown, and a change report. This is the exact artefact suppliers, wholesalers and retailers are struggling to produce right now.
3. **Recipe calculator on CoFID (OGL) with provenance on every value and portion-first output**, exporting a UK nutrition declaration. Loose-item matching included for own-made/PPDS-adjacent products (ingredients in descending weight order + allergen emphasis export serves the PPDS crowd's actual legal need).
4. **Source-watch + versioned data releases**: official overlays (DHSC/Quadram analyses) as reviewed candidate releases, never silent overwrites.

**Do NOT try to be yet:** a label-design/print suite (NutriCalc/Kafoodle territory, low differentiation); an EPOS/retail-systems integrator; a Brandbank replacement for branded GTIN data (paid, licensed, and already Trading Standards-assured); a lab-analysis substitute in its claims (always "database estimate"); a consumer app; or a multi-country product — the country-pack architecture holds the door open without walking through it.

## 6. Timing risks — reasons this could be wrong

1. **The paying segments are the served segments.** Nutritics holds EuroFIR Gold accreditation for recipe calculation; NutriCalc has operated since 1991; Brandbank owns the retailer data channel. ShelfScale's wedge is the open/auditable layer and the unserved long tail — if the strategy drifts toward "cheaper Nutritics," it loses.
2. **Free is already partially true.** Free single-product HFSS calculators exist (e.g., hfsscalculator.co.uk, which reads its thresholds from the DHSC guidance). The defensible product is bulk, dual-model, provenance-carrying scoring — not a calculator page.
3. **NPM 2018 outcome is pending.** If government drops or delays it, the dual-score urgency halves (the 2004/05 need remains). If adopted, there is a 12-month implementation scramble — being ready before the outcome is announced is the bet.
4. **Open source ≠ open data.** CoFID is OGL (fine); Open Food Facts is ODbL share-alike; Quadram's APIs are non-commercial; Brandbank data is paid licence. "Use all data we can find" only works with per-source licence gating, or the open-source release inherits other people's restrictions.
5. **Healthy Food Sales reporting could shift the centre of gravity** from product scores to sales-weighted portfolio metrics for large businesses. The data model should store scores in a form that aggregates by sales volume later, even though reporting rules aren't final.

**Verdict:** timing is right, arguably late-2026 is the best entry point in a decade: Scotland just went live, NI is consulting, schools have a Sept 2027 runway, and the NPM 2018 decision will force a national rescore. Build the open scoring-and-evidence layer first; sell hosting, support and feeds around it later.
