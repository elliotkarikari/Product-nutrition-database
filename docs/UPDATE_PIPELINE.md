---
type: process
status: draft
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Update pipeline: how ShelfScale stays current

ShelfScale's promise is not that its data never ages. It is that ageing is visible and updates are disciplined.

## The six steps

1. **Watch.** Each registered source is checked on its cadence in `data/source-register.yaml`: page change, file hash, ETag or last-modified, new publication, or terms change.
2. **Snapshot.** A detected change is captured as an immutable raw snapshot with fetch time and hash. The current release is untouched.
3. **Diff.** The candidate is compared with the current release: foods added or removed, values changed, rules changed, licence changed. The diff is written in plain language a maintainer can review.
4. **Validate.** Schema checks, unit checks, nutrient consistency checks, scorer fixtures and the match gold set run against the candidate.
5. **Review.** A maintainer reads the diff, checks the licence gate, and approves, rejects or parks the candidate. Model-assisted matches in the candidate are sampled for human spot checks.
6. **Release.** Approved candidates become a new data release with a version, a changelog and supersession links. Old releases remain reproducible.

## Hard rules

- Automation never promotes a candidate to the current release.
- A licence downgrade blocks release until a maintainer resolves it.
- A rule change (for example a scoring model revision) is released as a country pack change, never mixed silently into a data change.
- Every output names the data release and pack version that produced it.
- If a source disappears or its terms become unclear, its data is flagged, not quietly kept as if nothing changed.

## Watch cadences

- Official datasets and guidance: monthly.
- Official analysis reports and regulator news: monthly.
- Open product data exports: weekly snapshot candidates.
- Licensed feeds: per contract; terms reviewed quarterly.
- Legacy sample and portion datasets: static, re-verified yearly.

Until the watcher code exists, the monthly source check is run as a scheduled review against the register, and its findings are recorded in the project notes.
