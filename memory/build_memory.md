# ShelfScale build memory

Read after sync and before code. Updated 2026-11-05 (America/New_York).

## Project in five lines
ShelfScale Open is a UK-first nutrition data engine governed by [SPEC](../SPEC.md).
It preserves source evidence on imported nutrient and portion observations.
It exposes supplied-value and CoFID lookup assessment APIs, including bulk calls.
It computes UK NPM 2004/05 and a labelled NPM 2018 shadow result plus traffic lights.
Recipe calculation, label export and broader country packs remain planned.

## Verified state
- Branch: `shelfscale-open`; session started at `16c3398`. Audit `6f29f92`, fixes `574c82e`, Phase 4 `9316caaf39aac328f42760f2a10d40c423707890` pushed and read back. **Phase 5 implemented locally, push held for Railway key confirmation.** Resolve its commit with `git log -1 --format=%H -- memory/build_memory.md`; compare local/remote HEAD before work.
- **131 tests passed**, 2026-11-05, 7.863s. [Hardening verification](verification/2026-11-05-phase5-local.md); prior stages 103 → 111 → 123. CoFID 2,887 foods / 240,340 original observations; overlays add 713 observations across 11 matched foods plus 5,013 source-only. FPS 2,606 portions; sample weights 44 composites / 577 sub-samples.
- **Phase 4 live verified** at 2026-11-06 04:10 UTC: [health](https://product-nutrition-database-production.up.railway.app/health) HTTP 200, `{"status":"ok","models":{"uk-npm-2004/05":"in force","uk-npm-2018":"shadow model, not in force"}}`; real beef lookup HTTP 200, energy 523 kJ with new overlay provenance. [Response evidence](verification/2026-11-05-phase4-live.json). Live SHA unavailable; Phase 5 protection is not live yet.
- [Audit](../docs/CODEX_AUDIT.md): all eight findings addressed in code; no official-example score changed. [Rocky memory record](verification/2026-11-05-rocky-memory-round.md) reconstructed, primary evidence missing.

## Standing rules
- [Defensible data](decisions/defensible-data.md): three evidence tiers; gaps stay gaps.
- [FPS publication](decisions/fps-publication.md): owner decision; Crown copyright, NOT OGL; retain citation.
- [VJ exclusion](decisions/vj-never-publish.md): never copy/publish/use; retain guard.
- [Banding](decisions/no-rounding-before-banding.md): never round first.
- [Free sugars](decisions/free-sugars.md): caller input only; no total-sugar substitute.
- [FVN](decisions/fvn-2018-rulings.md): old derivation preserved; 22 DG exclusions for 2018, caller labels and model-specific flags.
- [Overlays](decisions/official-overlays.md): exact/established food and nutrient identities; original values retained.
- [FPS reconciliation](decisions/fps-reconciliation.md): ordered food/portion identity, ambiguity explicit, weights unchanged.
- [API hardening](decisions/api-hardening.md): required key, shared rolling quota, public root/health; hold push for Railway variable.
- [Identity](decisions/commit-as-elliot.md): Elliot; no agent co-author trailers.
- [Delivery](decisions/delivery-means-pushed.md): push and read back, otherwise local-only plus handoff.
- [Memory lifecycle](decisions/memory-lifecycle.md): read first; update each round; evidence over recollection; supersede decisions explicitly. Repo/live outrank memory; SPEC governs product behavior.

## Where things live
Canonical working directory: `/Users/elliotkarikari/Dev Projects/Product-nutrition-database`.

[SPEC](../SPEC.md) governs; [docs](../docs/) hold API, architecture, data model, source and roadmap detail; [register](../data/source-register.yaml) governs source status. [Snapshots](../data/raw/) hold manifests/attribution; [engine](../src/shelfscale/), [tests](../tests/), [FPS reconciliation](../docs/fps_reconciliation.csv) and [script](../scripts/reconcile_fps.py) are local evidence. API entry point: `src/shelfscale/api.py`; [railway.toml](../railway.toml) and [deployment guide](../docs/DEPLOYMENT.md) track runtime configuration; account settings remain uninspected. [INDEX](INDEX.md) lists all memory files.

## Open threads and owners
- **Codex:** Phase 5 implemented/tested; push held until Elliot confirms the Railway key is deployed, then rerun tests, push/read back and verify live health/authenticated lookup.
- **Elliot:** confirm SHELFSCALE_API_KEY is set/deployed on the existing Railway service; the token is now generated in ignored local `.env` (0600), ready for Railway setup and the final authenticated check. Never send the key in chat.
- **Rocky:** independently verify delivery; supply primary memory-round read-back. The reconstructed record is not a substitute. External watch/research schedules remain unverified here.
- **Elliot / future data review:** two apparent FPS weight differences and ambiguous pork require the physical book; additional tuber species identities, unmatched overlays and GA/FA processing need evidence before broader derivation.
- **Elliot / future implementer:** powder reconstitution, first user surface/CSV/recipe/label tools, watcher code, partnerships, other country packs and old-foods import remain parked or undecided (SPEC §12, register). Legacy history cleanup remains owner-controlled; VJ fix-forward exclusion is unchanged.

Local credential setup: [2026-11-05 verification](verification/2026-11-05-local-key-setup.md); no secret in memory.
