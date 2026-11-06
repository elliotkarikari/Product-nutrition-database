# When the law changes

ShelfScale scores every product under two models at once. Which one is the law today is configuration, in `data/laws.json`. The scoring engines (`src/shelfscale/npm.py`, `src/shelfscale/npm2018.py`) never read that file, so changing it cannot change a score.

## Statuses

- `in_force`: the law that applies today. At most one model.
- `shadow`: computed beside it, not in force (proposed or coming).
- `retired`: no longer in force. Still computed, so a past result can be reproduced and quoted.

Every score in every output carries a `law` label (model, name, version, status, role) and the data release. The page's "today" and "coming" framing follows the `role`, so it moves with the configuration.

## Procedure when NPM 2018 (or a successor) is adopted

1. Read the instrument that adopts it. Record the date it takes effect, the exact model version and any transition period.
2. In one commit, change `data/laws.json`: the adopted model to `in_force`, the old one to `retired` (or leave it `shadow` until its effective date, if the instrument says so). Update `note` and `decided`. Change nothing else in that commit.
3. Run the whole suite. `tests/test_laws.py` shows that a flip changes labels and framing and leaves every score identical. All worked-example tests must pass unchanged.
4. Record a decision in `memory/decisions/` that supersedes `law-status-config.md` by name, citing the instrument.
5. Push. Check `/health` and `/api` show the new statuses, and that a known product's scores are unchanged on the page.

## What does not change

- Both engines keep running. Bulk runs and exports keep both scores.
- Field names stay stable for callers, including `verdict_changes_under_2018`, which compares the 2004/05 verdict with the 2018 one whichever is in force.
- Historical results stay reproducible: same inputs and data release give the same scores, now labelled with the current statuses.

## A successor model

A new model (for example a 2030 revision) needs its own engine module, its own worked-example tests from the published guidance, and an entry in `data/laws.json`. Adding it does not touch the existing engines.
