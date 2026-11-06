# Data first: the dataset is the centre, scoring its flagship use

Status: proposed, on branch `shelfscale-data-first` only. Elliot reviews the look before it goes live. If adopted, it supersedes the site framing in [product-direction.md](product-direction.md) (rule 1's "every screen answers three scoring questions"); that file's other rules (products as sold, small producers, copy rules, law and release on every score) carry over unchanged.

Decision date: 2026-11-06

Decision maker: Elliot Karikari (brief of 2026-11-06). The builder chose layout, routes and the drafted copy within it.

Decision:
1. The data product is the centre of ShelfScale; scoring is the flagship use of the data, not the frame of the site.
2. Four top-level destinations on every page: Browse the data (`#/`, `#/browse/<group>`, `#/food/<id>`), Score a product (`#/score`, `#/score/<id>`, plus recipe and label), Score your range (`#/range`), Download the data (`#/download`).
3. Home leads with the release: hero line, counts from `/api`'s `release` block, and the 14 CoFID main groups as the oversized subject. The raisins flip is one panel.
4. The release is downloadable as CSV with no key, built from the same in-process data the API serves (`src/shelfscale/release.py`), with a manifest of counts, checksums and attribution.
5. Food pages lead with the food as sold; the dual-law ticket is one panel (first only in the score view). Each food downloads as CSV.
6. Score your range names its two modes (your figures, ShelfScale reference data) in framing, rows and export.

Drafted, not settled: the hero line and lede in `app.js` (`HERO`, `HERO_LEDE`) and the release citation (`release.CITATION`).

Evidence: [verification/2026-11-06-data-first.md](../verification/2026-11-06-data-first.md); tests/test_release.py; tests/test_page_copy.py.
