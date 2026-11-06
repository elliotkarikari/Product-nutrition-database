# ShelfScale build memory

Read after sync and before code. Updated 2026-11-05 (America/New_York).

## Project in five lines
ShelfScale Open is a UK-first nutrition data engine governed by [SPEC](../SPEC.md).
It preserves source evidence on imported nutrient and portion observations.
It exposes supplied-value and CoFID lookup assessment APIs, including bulk calls.
It computes UK NPM 2004/05 and a labelled NPM 2018 shadow result plus traffic lights.
Recipe calculation, label export and broader country packs remain planned.

## Verified state
- Branch: `shelfscale-open`; session started at `16c3398`; audit `6f29f92` and fixes `574c82e` pushed and read back. Phase 4 checked base: `574c82e1db97bc976d2ffa4824af1d3c524c47a3`; resolve this round’s commit with `git log -1 --format=%H -- memory/build_memory.md` and check local/remote HEAD every session.
- **123 tests passed**, 2026-11-05, 7.183s. [Phase 4 verification](verification/2026-11-05-phase4.md). CoFID: 2,887 foods / 240,340 original observations; official overlays add 713 observations across 11 matched foods, retaining history; 5,013 source-only. FPS 2,606 portions; sample weights 44 composites / 577 sub-samples.
- Live [Railway health](https://product-nutrition-database-production.up.railway.app/health), last checked after fixes push: HTTP 200, `{"status":"ok","models":{"uk-npm-2004/05":"in force","uk-npm-2018":"shadow model, not in force"}}`. Deployment SHA/settings not exposed/inspected; Phase 4 live read-back follows push.
- [Audit](../docs/CODEX_AUDIT.md): numeric/HTTP/docs/socket and FVN/provenance/FPS findings addressed. Required-key/rate-limit/root hardening is next. [Rocky memory record](verification/2026-11-05-rocky-memory-round.md) is explicitly reconstructed; primary evidence remains missing.

## Standing rules
- [Defensible data](decisions/defensible-data.md): three evidence tiers; gaps stay gaps.
- [FPS publication](decisions/fps-publication.md): owner decision; Crown copyright, NOT OGL; retain citation.
- [VJ exclusion](decisions/vj-never-publish.md): never copy/publish/use; retain guard.
- [Banding](decisions/no-rounding-before-banding.md): never round first.
- [Free sugars](decisions/free-sugars.md): caller input only; no total-sugar substitute.
- [FVN](decisions/fvn-2018-rulings.md): old derivation preserved; 22 DG exclusions for 2018, caller labels and model-specific flags.
- [Overlays](decisions/official-overlays.md): exact/established food and nutrient identities; original values retained.
- [FPS reconciliation](decisions/fps-reconciliation.md): ordered food/portion identity, ambiguity explicit, weights unchanged.
- [Identity](decisions/commit-as-elliot.md): Elliot; no agent co-author trailers.
- [Delivery](decisions/delivery-means-pushed.md): push and read back, otherwise local-only plus handoff.
- [Memory lifecycle](decisions/memory-lifecycle.md): read first; update each round; evidence over recollection; supersede decisions explicitly. Repo/live outrank memory; SPEC governs product behavior.

## Where things live
Canonical working directory: `/Users/elliotkarikari/Dev Projects/Product-nutrition-database`.

[SPEC](../SPEC.md) governs; [docs](../docs/) hold API, architecture, data model, source and roadmap detail; [register](../data/source-register.yaml) governs source status. [Snapshots](../data/raw/) hold manifests/attribution; [engine](../src/shelfscale/), [tests](../tests/), [FPS reconciliation](../docs/fps_reconciliation.csv) and [script](../scripts/reconcile_fps.py) are local evidence. API entry point: `src/shelfscale/api.py`; [railway.toml](../railway.toml) and [deployment guide](../docs/DEPLOYMENT.md) track runtime configuration; account settings remain uninspected. [INDEX](INDEX.md) lists all memory files.

## Open threads and owners
- **Codex:** Phase 4 remote/live read-back, then Phase 5 authentication, rolling 60/minute quota and root summary; hold hardening push until Elliot confirms the Railway key is deployed.
- **Elliot:** set SHELFSCALE_API_KEY on existing Railway service at that checkpoint; never send the key in chat.
- **Rocky:** independently verify delivery; supply primary memory-round read-back. The reconstructed record is not a substitute. External watch/research schedules remain unverified here.
- **Elliot / future data review:** two apparent FPS weight differences and ambiguous pork require the physical book; additional tuber species identities, unmatched overlays and GA/FA processing need evidence before broader derivation.
- **Elliot / future implementer:** powder reconstitution, first user surface/CSV/recipe/label tools, watcher code, partnerships, other country packs and old-foods import remain parked or undecided (SPEC §12, register). Legacy history cleanup remains owner-controlled; VJ fix-forward exclusion is unchanged.
