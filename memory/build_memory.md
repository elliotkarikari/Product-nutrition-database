# ShelfScale build memory

Read after sync and before code. Updated 2026-11-06 (America/New_York).

## Project in five lines
ShelfScale Open is a UK-first nutrition data engine governed by [SPEC](../SPEC.md).
It preserves source evidence on imported nutrient and portion observations.
It exposes supplied-value and CoFID lookup assessment APIs, including bulk calls.
It computes UK NPM 2004/05 and a labelled NPM 2018 shadow result plus traffic lights.
The page at `/` serves small producers: today's and the coming law's verdict, with receipts, for one product, a whole range (CSV in and out) or a recipe and its label.

## Verified state
- **Data-first round (2026-11-06), branch `shelfscale-data-first` from `48705b3c`, NOT merged, Railway untouched:** release files and `/download/*`, `/api` gains a `release` counts block, group browse, four-destination navigation, data-led home, downloads page, food-first food pages with per-food CSV, range modes named. **190 tests passed.** [Verification](verification/2026-11-06-data-first.md), [decision](decisions/data-first.md) proposed only. Production stays on `shelfscale-open`; Elliot decides on the look. Hero line and citation are drafts.
- **Round 2 (2026-11-06), base `1318abc`:** law status as configuration (data/laws.json), Your range (`/ui/bulk`), matching assistant (`/ui/match`, Jev gate when TYPESAFE_API_KEY is set), as-sold units with measured ranges, copy and visual rewrite. **167 tests passed.** [Verification](verification/2026-11-06-round2.md). Live unverified until Elliot pushes (session has no GitHub write access). Resolve the round head with `git log -1 --format=%H -- memory/build_memory.md`.
- **UI round (2026-11-06), base `cec82dcb22b1d5e9ae5623fe8da5df17d5755f30`:** page at `/`, summary moved to `/api`, page routes `/ui/search`, `/ui/food/<id>`, `POST /ui/recipe` with their own 300/min quota; recipe and label engine. **150 tests passed** before push (131 + 19 new), [log](verification/2026-11-06-ui-tests.txt). Live verification: see the UI verification record once added; until then treat live state as unverified.
- Branch: `shelfscale-open`; session started at `16c3398`. Audit `6f29f92`, fixes `574c82e`, Phase 4 `9316caaf39aac328f42760f2a10d40c423707890` pushed and read back. **Phase 5 pushed and live at `994d2c1a1a1cc39c0f699af1469d7a3dd516aba4`**, after Elliot confirmed the variable. This final round records deployment evidence; resolve its commit with `git log -1 --format=%H -- memory/build_memory.md`; compare local/remote HEAD before work.
- **131 tests passed**, 2026-11-05, 7.799s before final record push. [Deployment verification](verification/2026-11-05-phase5-deployed.md); prior stages 103 → 111 → 123. CoFID 2,887 foods / 240,340 original observations; overlays add 713 observations across 11 matched foods plus 5,013 source-only. FPS 2,606 portions; sample weights 44 composites / 577 sub-samples.
- **Phase 5 live verified:** public [health](https://product-nutrition-database-production.up.railway.app/health) and root HTTP 200, both exposing revision `994d2c1a`; health returns status ok, 2004/05 “in force”, 2018 “shadow model, not in force”. Unauthenticated lookup 401; authenticated beef lookup 200 with energy 523 kJ and overlay provenance. [Response evidence](verification/2026-11-05-phase5-deployed.json).
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
- [API hardening](decisions/api-hardening.md): required key, shared rolling quota, public root/health; Railway-variable checkpoint satisfied.
- [Identity](decisions/commit-as-elliot.md): Elliot; no agent co-author trailers.
- [Delivery](decisions/delivery-means-pushed.md): push and read back, otherwise local-only plus handoff.
- [Product direction](decisions/product-direction.md): today, coming, receipts; products as sold; small producers. Proposed successor framing on branch only: [data first](decisions/data-first.md).
- [Law status](decisions/law-status-config.md): statuses in data/laws.json; adoption in docs/LAW_CHANGE.md.
- [Matching](decisions/matching.md): retrieval proposes, Jev gates, a person confirms; thresholds provisional.
- [As sold](decisions/as-sold-units.md): unit ranges from sampling purchases; draft links need confirmation.
- [UI design](decisions/ui-design.md): dual-law ticket, tear for a flip, shelf-edge ticket motif, one signal colour for taps; scores only from the service.
- [Label from CoFID](decisions/label-from-cofid.md): user-guide conversions to label conventions; scores stay on CoFID values.
- [Memory lifecycle](decisions/memory-lifecycle.md): read first; update each round; evidence over recollection; supersede decisions explicitly. Repo/live outrank memory; SPEC governs product behavior.

## Where things live
Canonical working directory: `/Users/elliotkarikari/Dev Projects/Product-nutrition-database`.

[SPEC](../SPEC.md) governs; [docs](../docs/) hold API, architecture, data model, source and roadmap detail; [register](../data/source-register.yaml) governs source status. [Snapshots](../data/raw/) hold manifests/attribution; [engine](../src/shelfscale/), [tests](../tests/), [FPS reconciliation](../docs/fps_reconciliation.csv) and [script](../scripts/reconcile_fps.py) are local evidence. API entry point: `src/shelfscale/api.py`; page in `src/shelfscale/web/`, page data in `ui_api.py`, recipes in `recipe.py`, declaration in `label.py`; [railway.toml](../railway.toml) and [deployment guide](../docs/DEPLOYMENT.md) track runtime configuration; account settings remain uninspected. [INDEX](INDEX.md) lists all memory files.

## Open threads and owners
- **Elliot:** maintain/rotate the service key securely in Railway and ignored local `.env` (0600); never send it in chat. Deployment and authenticated verification are complete.
- **Rocky:** independently verify delivery; supply primary memory-round read-back. The reconstructed record is not a substitute. External watch/research schedules remain unverified here.
- **Elliot / future data review:** two apparent FPS weight differences and ambiguous pork require the physical book; additional tuber species identities, unmatched overlays and GA/FA processing need evidence before broader derivation.
- **Elliot:** review label-from-cofid and the public page quota; review the 24 draft portion links (set status to reviewed) and spot-check the matching evaluation labels; run scripts/evaluate_matching.py with TYPESAFE_API_KEY and set thresholds; set TYPESAFE_API_KEY on Railway; install the Claude GitHub app if agents should push.
- **Elliot / future implementer:** powder reconstitution (flagged in the page, not computed), cooking yields, a reviewed portion-to-food mapping, CSV tools, watcher code, partnerships, other country packs and old-foods import remain parked or undecided (SPEC §12, register). Legacy history cleanup remains owner-controlled; VJ fix-forward exclusion is unchanged.

Local credential setup: [2026-11-05 verification](verification/2026-11-05-local-key-setup.md); no secret in memory.
