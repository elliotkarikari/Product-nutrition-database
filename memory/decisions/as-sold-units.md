# Products as sold: units, ranges and links

Status: active; supersedes portion-links.md

Decision date: 2026-11-06

Decision maker: Elliot Karikari (scores as sold; loose push); implementing agent (mechanics).

Decision: The food and range views show the unit as sold. Packaged: the declared pack weight the user gives, labelled as theirs. Loose: the sampling reports' sub-samples, each the average of several items from one purchase, so the range shown is between purchases and says so. Edible weight per purchase is weight x that purchase's edible proportion when the CoFID food is per 100 g edible; whole weight when the CoFID food is weighed with skin, stone or peel. The per-unit band is coloured by the traffic-light engine at both ends; a band that crosses a per-portion limit names both colours. The per-100 g verdict never moves. No unit evidence means no unit; nothing is invented.

Links: exact name (as FPS) and data/mapping/portion_links.json entries with status "reviewed" apply automatically; status "draft" entries (24, builder-drafted) are offered for a person to confirm and never apply on their own. Raw item weights are never linked to cooked or stewed foods. Loose status comes from the author's 2023 retail list sale formats (loose, counter, bunch, fresh produce, fresh bakery).

Counts (70 loose foods in the retail list): unit weight before 4, measured range 3; unchanged automatically; 14 and 13 once the 10 relevant drafts are reviewed. Legacy per-product sampling CSVs added no spread: none reproduces the report's stated average over its full table (tomatoes matched on 5 of 22 rows only, not evidence). See memory/verification/2026-11-06-round2.md.

Evidence: src/shelfscale/as_sold.py, retail_core.py; tests/test_bulk_matching.py TestAsSold (mango band crosses on sugars: amber at 281 g, red at 528 g).
