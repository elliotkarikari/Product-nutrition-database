---
type: product-spec
status: draft
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# ShelfScale Open: product definition

## Problem

A food business, researcher or software builder who needs trustworthy nutrition values has to assemble them from national food tables, one-off government analysis reports, product labels, commercial catalogues and their own recipes. The sources use different formats, vintages, nutrient definitions and licences. The rules that turn values into a label or a score then differ by country.

The result is slow manual work, silent copying of stale values, and numbers nobody can defend because nobody recorded where they came from.

## What ShelfScale is

An open-source engine and data pipeline that:

- matches a food, ingredient, product or recipe line to the best available composition evidence;
- keeps the evidence attached to every value;
- applies one country's rules through a country pack;
- shows results portion first, with the per-100 g basis available and labelled;
- updates through reviewed, versioned data releases when sources change.

## Who it serves first (to be confirmed by current-needs research)

- Small and mid-size UK food producers who must label products and answer HFSS questions without a regulatory team.
- Bakeries, delis and caterers producing pre-packed for direct sale foods.
- Builders and researchers who need UK nutrition data in a clean, provenance-carrying form.

## Principles

1. Portion first in presentation; per 100 g for comparison and compliance.
2. Provenance is part of the value, not a footnote.
3. Updates are releases with diffs, never silent overwrites.
4. Licence status is recorded before ingestion, and enforced at export.
5. Estimates are labelled with their basis and confidence.

## Non-goals

- Not a laboratory. ShelfScale does not claim database estimates are lab analysis.
- Not legal advice. Scores and labels are calculation aids; the business remains responsible for its labels.
- Not a scrape-everything database. Sources are used within their terms.
- Not a global product on day one. The UK pack comes first; other countries are added pack by pack.

## Business shape

Open-source core, decided November 5, 2026, so the data work can be shared, checked and improved in the open. Any hosted service, support or commercial data partnerships are later decisions and are not assumed here.
