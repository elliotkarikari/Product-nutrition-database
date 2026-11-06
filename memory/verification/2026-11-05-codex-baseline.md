# Codex baseline verification

Verifier: Codex. Date: 2026-11-05 America/New_York; final data probe 2026-11-06T03:25:00Z.
Scope: evidence for the memory seed, not a completed Part A audit or official-source revalidation.
Verified code head: 3077478c20a6b163149f45470ebb90c47f0264a4.

- Sync: `git status --porcelain=v1` showed only untracked `.DS_Store`; stopped, then owner authorized fetching and continuing. Preserved that file. `git fetch origin shelfscale-open`, `git rev-list --left-right --count HEAD...origin/shelfscale-open` gave 0/7; `git merge --ff-only origin/shelfscale-open` succeeded. `git rev-parse HEAD origin/shelfscale-open` returned the exact head above twice.
- Tests: `PYTHONPATH=src python3 -m unittest discover -s tests -v` passed **103 tests in 6.028s**. First sandbox run executed 91 tests with two setup errors because local socket binding was denied; reran with approved socket access. Successful run emitted two unclosed-socket ResourceWarnings. Log is retained beside this record.
- Existing tests exercised six 2004/05 and 17 2018 worked-example fixtures, traffic-light fixtures, boundary/density rules, supplied and lookup bulk paths, missing free sugars, checksum refusal, duplicate codes, FPS provenance and VJ exclusion. Passing fixtures are not fresh validation against official publications.
- Raw-snapshot import: `PYTHONPATH=src python3` calling `cofid_release()` produced 2,887 foods and 240,340 observations. `tests/test_cofid.py` also checks 2,886 distinct codes, duplicate 13-669, and unique food IDs.
- FPS suite reconciles 2,652 CSV rows: 2,606 imported and 46 excluded; citation and rights wording tests pass. The existing wording scan covers specified docs/register/snapshot files, not all future files. This round additionally reviewed the new memory wording. No physical-book validation performed.
- Sampling suite: 44 imported food composites, 577 sub-samples. Tests reconcile report text tables and stated averages; no fresh visual PDF review performed.
- Direct lookup: `lookup_and_assess({'code':'14-834','free_sugars_g':0})` gives 2004/05 score 5 / less_healthy true; 2018 score 1 / less_healthy false.
- Live: `curl -sS --max-time 30 -w '\nHTTP %{http_code}\n' https://product-nutrition-database-production.up.railway.app/health` returned HTTP 200 and `{"status": "ok", "models": {"uk-npm-2004/05": "in force", "uk-npm-2018": "shadow model, not in force"}}`. Initial sandbox DNS attempt failed; approved network retry succeeded. Health has no deployment SHA; it does not prove which commit Railway serves or that current law matches the labels.
- Inspection: `api.py` exposes health and four POST routes; no authentication/rate limiter or root-summary handler. No tracked Railway config was found. Railway account, deployment settings/start command and release identity were not checked.
- Memory correction: SPEC §14 names an old 2f44f9c handover; retained as history, not current head. API FVN review flags are documentation flags only; code uses D/F/G prefixes with DA/DR exclusions. Queued phase names cannot be reconciled with docs/ROADMAP.md without the actual briefs.
- Missing evidence: no tracked docs/CODEX_AUDIT.md or primary Rocky read-back logs found. No claim that Part A is complete. No adversarial API audit, independent official-source check, or full licensing audit performed this round.
