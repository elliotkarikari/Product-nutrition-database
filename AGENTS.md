# ShelfScale session instructions

1. Sync check first: inspect branch/status, fetch `origin`, and compare local/remote `shelfscale-open`. Preserve local work; stop on divergence or unexpected changes. Do not reset or overwrite to sync. `main` is legacy and is not the ShelfScale work branch.
2. Immediately after sync, read `memory/build_memory.md`, then relevant linked decisions and SPEC before touching code. Follow the same workflow regardless of agent identity.
3. At the end of every work round, update the memory summary with checked head, dated tests and state changes; add a verification event for checks and a decision file for new decisions. Commit these with that round’s work. Update `memory/INDEX.md` for every new file. Record the checked base SHA and resolve the resulting round commit through Git rather than inventing a self-referential SHA.
4. Keep entries short, dated and evidenced. No transcripts or unsupported state. Record failed/unrun checks and historical reports as such. Repository/live evidence overrides memory; SPEC governs product behavior. Correct conflicts in the same round with a verification note.
5. Supersede decisions explicitly: mark the old file superseded by its named successor and create the new decision. Never silently rewrite a decision. Keep `build_memory.md` a quick summary and move detail to linked files.
6. Use Elliot’s configured Git identity without agent co-author trailers. Delivery requires push and remote read-back; otherwise report local-only and supply a patch/bundle. No deployment or implementation of unverified queued briefs is implied.

Before creating or merging any PR, follow the owner’s global paired Ponytail and thermo-nuclear review gate (maximum three paired rounds; do not skip either review). This task does not require creating a PR.
