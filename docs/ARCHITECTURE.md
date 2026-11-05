---
type: architecture
status: draft
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Architecture

## One core, many country packs

**Canonical core** (country-neutral):

- Food and product identity, including GTIN and market availability.
- Ingredient and recipe structures.
- Nutrient observations with full provenance.
- Portion and unit-weight observations, edible-portion factors and cooking yields.
- Match decisions between a named item and a composition entry, with method and confidence.

**Country pack** (one per market):

- The official composition dataset and its overlays.
- Nutrient definitions and methods (for example AOAC fibre versus Englyst fibre; salt versus sodium).
- Label fields, order, units, rounding and reference intakes.
- Allergen list and claim rules.
- Scoring models and front-of-pack schemes.
- Language, food names and portion conventions.
- Licence and attribution text for every source in the pack.

A jurisdiction layer sits inside a country pack where rules differ inside the country. The UK pack must distinguish England, Scotland, Wales and Northern Ireland for HFSS promotion and placement uses.

## Data layers

1. **Raw snapshots.** Immutable copies or fingerprints of what a source published, with fetch time and hash. Never edited.
2. **Staging.** Parsed and normalised candidate data. Nothing here is public truth.
3. **Canonical observations.** Reviewed values with provenance, status (current, superseded, estimate) and supersession links.
4. **Country pack transforms.** Deterministic calculations: declarations, traffic lights, NPM, portion views.
5. **Outputs.** API responses, label renders, exports. Every output can be traced to a data release and a pack version.

## Matching

Order of evidence for a specific product (v1 policy, November 2026: defensible sources only):

1. Manufacturer specification or current label for that exact GTIN.
2. Licensed current product catalogue data.
3. Official generic composition entry (CoFID in the UK pack).
4. Model-assisted match to one of the sources above, marked as an estimate of the match. The values still come from the defensible source; only the match is estimated.

Anything that cannot be matched to one of these is reported as a gap. It is never filled from crowd-sourced, community or scraped data. Crowd-sourced sources such as Open Food Facts are excluded from the evidence base until the product is solid and the decision is revisited.

Match decisions are data. Once reviewed, they are frozen into a release; they are not re-decided live by a model on every request.

## Validation gates

- Schema and unit checks on every import.
- Nutrient range and internal consistency checks (for example energy versus macronutrients).
- Scorer fixtures: the NPM implementation must reproduce published worked examples and boundary cases in `tests/`.
- Match gold set: a human-checked set of matches, loose items included, with precision reported per release.
- Licence gate: a release cannot contain data whose licence forbids that release's use.

## Update flow

Watch, snapshot, diff, validate, review, release. See `UPDATE_PIPELINE.md`. No step may be skipped by automation; automation prepares, humans promote.
