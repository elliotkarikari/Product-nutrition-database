---
type: roadmap
status: draft
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Roadmap

## Phase 0: foundation (done, November 2026)

- Repository scaffold, MIT licence for code, licence-boundary rules for data.
- Product, architecture and data model documents.
- Source register with watch cadences.
- UK NPM 2004/05 scorer implemented with unit tests, replacing the legacy repo's stub approach.

## Phase 1: UK data core

- CoFID 2021 importer into canonical observations, with attribution and per-value provenance.
- Portion-size and fruit-and-vegetable sample imports as portion observations, with periods and spreads.
- UK traffic lights module, ported and tested against FSA thresholds.
- Match gold set v1: human-checked matches including loose items; precision reported.

## Phase 2: freshness

- Watcher code for registered sources: hash and change detection, candidate snapshots, plain-language diffs.
- Official overlay imports: DHSC/Quadram category analyses published since CoFID 2021 (milk, beef, and successors), superseding only what they measured.
- Release tooling: versioned data releases with changelogs and rollback.

## Phase 3: first user surface

- Recipe calculator: plain-language ingredients matched to canonical foods, portion-first results.
- UK outputs: nutrition declaration, traffic lights, NPM score with input evidence shown.
- Label export for small producers, with the estimate basis printed on the output.

## Phase 4: community and second country

- Contribution flow for corrections and new matches, with review and licence checks.
- Country pack interface documented so a second pack (Ireland or an EU state, discovered through EuroFIR) can be added without touching the core.
