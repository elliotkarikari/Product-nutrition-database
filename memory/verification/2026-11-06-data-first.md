# Data-first round verification

Date: 2026-11-06 (America/New_York). Branch `shelfscale-data-first`, cut from `shelfscale-open` at `48705b3c` (local head; a fresh clone of origin `shelfscale-open` read back the same commit, `48705b3`). Not merged; Railway untouched.

## Tests (Python 3.10.12, unittest, in the session's Linux shell on the Mac's working copy)
- `a9e60acc` release files, counts, group browse, download routes: **181 passed** (167 + 14).
- `e3dc92ec` page: navigation, home, downloads page, food reorder, range modes: **190 passed** (+ 9: the page counts test and 8 page and copy tests). [Log](2026-11-06-data-first-tests.txt).
- The project declares `requires-python >=3.11`; this shell has 3.10.12 and the suite passed there. Not rerun on 3.11+ in this session.

## Counts test
`tests/test_release.py`: `summary()` equals independently computed values (2,887 foods; 12 foods with an applied as-sold unit; 21 register entries); `GET /api` returns `release` equal to `summary()`; the home renderer shows that block unchanged and restates no count. The page is plain JavaScript, so the parity is proved by construction plus a static check, not by running the browser in the suite. In a headless Chrome run the rendered home counts read 2,887 / 12 / 21, matching `/api`.

## Release build
Deterministic (two builds, identical SHA-256). foods 2,887 rows; nutrient_observations 241,053 rows (87.7 MB; 3.7 MB gzipped on the wire); portions 2,642; scores 2,887; match_decisions 2,691 (visitor confirmations: 0, stated on the page). Build about 6 s at startup.

## Browser checks (headless Chrome against the branch files, served by the branch code)
Home, food, score view, group, downloads and range at 390 px and 1366 px: no console errors; no horizontal page scroll after the grid fix (the food page's per-unit band table now scrolls inside its panel; it widened the page at phone width before). Range run with one own-figures row and one CoFID row: both modes shown on rows and in the CSV export's `scored_from` column.

## Not verified here
Push and remote read-back (no GitHub write from this session); Rocky's ten-second test; Python 3.11+.
