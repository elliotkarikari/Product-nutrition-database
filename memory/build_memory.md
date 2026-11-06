# ShelfScale build memory

Read after sync and before code. Updated 2026-11-05 (America/New_York).

## Project in five lines
ShelfScale Open is a UK-first nutrition data engine governed by [SPEC](../SPEC.md).
It preserves source evidence on imported nutrient and portion observations.
It exposes supplied-value and CoFID lookup assessment APIs, including bulk calls.
It computes UK NPM 2004/05 and a labelled NPM 2018 shadow result plus traffic lights.
Recipe calculation, label export and broader country packs remain planned.

## Verified state
- Branch: `shelfscale-open`; synchronized base/code head: `3077478c20a6b163149f45470ebb90c47f0264a4`. This memory round changes documentation only. Resolve its resulting commit with `git log -1 --format=%H -- memory/build_memory.md`; check current local/remote HEAD every session.
- **103 tests passed**, last run 2026-11-05 after memory creation; two socket ResourceWarnings. [Final check](verification/2026-11-05-codex-memory-check.md). CoFID: 2,887 foods / 240,340 observations; FPS: 2,606 portions; sample weights: 44 composites / 577 sub-samples. [Commands, evidence and limits](verification/2026-11-05-codex-baseline.md).
- Live [Railway health](https://product-nutrition-database-production.up.railway.app/health): HTTP 200, `{"status":"ok","models":{"uk-npm-2004/05":"in force","uk-npm-2018":"shadow model, not in force"}}`. Labels are observed responses, not independently verified legal status. Deployment SHA/settings unverified.
- [Independent audit completed](../docs/CODEX_AUDIT.md) at 16c3398; 103 tests pass; fixes pending. [Rocky record gap](verification/2026-11-05-rocky-record-gap.md) is not a passed verification.

## Standing rules
- [Defensible data](decisions/defensible-data.md): three evidence tiers; gaps stay gaps.
- [FPS publication](decisions/fps-publication.md): owner decision; Crown copyright, NOT OGL; retain citation.
- [VJ exclusion](decisions/vj-never-publish.md): never copy/publish/use; retain guard.
- [Banding](decisions/no-rounding-before-banding.md): never round first.
- [Free sugars](decisions/free-sugars.md): caller input only; no total-sugar substitute.
- [FVN](decisions/fvn-derivation.md): caller override, DA exclusion, DR gap, documented group reviews.
- [Identity](decisions/commit-as-elliot.md): Elliot; no agent co-author trailers.
- [Delivery](decisions/delivery-means-pushed.md): push and read back, otherwise local-only plus handoff.
- [Memory lifecycle](decisions/memory-lifecycle.md): read first; update each round; evidence over recollection; supersede decisions explicitly. Repo/live outrank memory; SPEC governs product behavior.

## Where things live
Canonical working directory: `/Users/elliotkarikari/Dev Projects/Product-nutrition-database`.

[SPEC](../SPEC.md) governs; [docs](../docs/) hold API, architecture, data model, source and roadmap detail; [register](../data/source-register.yaml) governs source status. [Snapshots](../data/raw/) hold manifests/attribution; [engine](../src/shelfscale/), [tests](../tests/), [FPS reconciliation](../docs/fps_reconciliation.csv) and [script](../scripts/reconcile_fps.py) are local evidence. API entry point: `src/shelfscale/api.py`; Railway configuration is external/unverified, with no tracked railway.toml at baseline. [INDEX](INDEX.md) lists all memory files.

## Open threads and owners
- **Codex:** implement the ranked audit fixes, then authorized Phase 4/5; hold hardening push for the Railway key checkpoint.
- **Rocky:** supply primary read-back evidence; independently verify the delivered memory round. External watch/research schedules are not verifiable here (SPEC §§9, 14).
- **Claude / Elliot:** locate and reconcile queued Phase 4/5 briefs before implementation. No briefs are in the checkout; docs/ROADMAP.md uses a different Phase 4. Exact queued scope and five rulings are unverified, so not copied as project state.
- **Elliot (rulings), Claude (implementation):** SPEC §12 leaves 2018 tubers/seeds and powder reconstitution open. GA/FA review is documented, not a structured API flag. Official overlays remain planned in the register; API auth/rate limits/root summary and tracked deployment config are absent.
- **Elliot:** first user surface, hosted commercial offering, data partnerships (SPEC §12); any legacy history cleanup (docs/LEGACY_INVENTORY.md).
- **Elliot / future implementer:** parked CoFID old foods, US pack and other countries (register); recipe/label tools and watcher code (SPEC §11). Assignment beyond owner approval remains unconfirmed.
