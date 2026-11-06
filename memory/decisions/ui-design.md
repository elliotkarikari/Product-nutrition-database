# First user interface: concept and motif

Status: active

Decision date: 2026-11-06

Decision maker: Elliot Karikari (brief: product flow, design material, non-negotiables); the implementing agent chose layout, motif and copy within it.

Decision: The page is built around one fact, a food under two laws at once. Every food and recipe gets one score ticket split by a perforation: today's law (NPM 2004/05) on the left, the 2018 model on the right. When the verdict changes between models the ticket tears along a zigzag, the 2018 half drops and turns, and a "Verdict flips" stamp appears; the home page teaches this with a key ticket that carries labels, not numbers. Shape motif: the shelf-edge ticket, a label with punched half-circle notches, used on every panel, row, chip and button. One signal colour (ultramarine) marks only tappable things; traffic-light colours appear only as data and always with a word (Low, Medium, High). Three planes: giant background type (the food or recipe name), the ticket, then controls. Portion-first: the food view opens on a real portion where one of 10 g or more is on record.

Rules carried into the page: scores come only from the service; per-portion figures on the food view are display scaling of the service's values; display rounding never feeds a score; caller-supplied figures are labelled on the ticket ("Scored with your figures"); every value has a one-tap source card (dataset, edition, period, locator, rights, citation, record id); FPS weights carry the book citation and rights; no em dashes in copy; no invented sample data. Recipes live in browser local storage only.

Serving: the service serves plain HTML, CSS and JavaScript at `/`; the JSON summary moved to `/api`. Page routes run in-process rather than calling the keyed API over HTTP: same functions, no key handling at all, so the browser cannot see it. They have their own public quota (300 per minute per process) and accept one food or one recipe per request.

Reasoning: dual scoring is ShelfScale's distinctive output and the flip is its most important result, so it gets the strongest visual treatment, carried by shape and words rather than colour. A shelf-edge ticket belongs to the product's world (shelves, labels, HFSS placement). In-process routes are simpler than a self-calling proxy and give the same guarantee.

Evidence: src/shelfscale/web/; src/shelfscale/ui_api.py; src/shelfscale/api.py; tests/test_ui.py (serving, quota separation, score parity with /v1/lookup and /v1/assess, provenance).

Open: the page routes are public. Their quota bounds load, not who calls them. Whether a public scoring surface is acceptable long term is Elliot's call.
