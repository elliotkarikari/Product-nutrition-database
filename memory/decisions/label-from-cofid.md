# UK nutrition declaration from CoFID

Status: active

Decision date: 2026-11-06

Decision maker: the implementing agent, applying the CoFID 2021 user guide; recorded for Elliot's review.

Decision: The declaration (energy kJ and kcal, fat, saturates, carbohydrate, sugars, protein, salt; per 100 g and per portion) is converted from CoFID by the user guide's own rules ("Food labelling", pages 15 to 16): protein = total nitrogen x 6.25; carbohydrate by weight = CHO / 1.05, or starch / 1.10 plus the rest / 1.05 when starch is more than half of CHO; sugars by weight = total sugars with sucrose and lactose divided by 1.05 and other sugars as given (maltose as given, as the guide's wording says); energy with the Regulation's factors (carbohydrate 17/4, protein 17/4, fat 37/9, AOAC fibre 8/2, alcohol 29/7); salt = sodium x 2.5. Conversion is per ingredient, then summed. Display rounding follows the EC tolerance guidance's rounding table (December 2012) and is applied last, to per 100 g and per portion separately.

Gaps stay visible: a line an ingredient cannot supply is not declared, naming the ingredient; energy that leaves out fibre or alcohol because CoFID records no value says so by name. Polyols, organic acids and salatrims have no CoFID columns and are not counted. The "salt is from naturally occurring sodium" statement is not generated (ShelfScale cannot know whether salt was added).

Scores are unchanged: NPM and traffic lights still use CoFID values as listed, as lookup mode always has. The page says so beside the recipe figures.

Reasoning: CoFID carbohydrate and sugars are monosaccharide equivalents and its energy uses different factors (user guide pages 10 and 15 to 16), so CoFID values printed directly would misstate a legal declaration.

Evidence: src/shelfscale/label.py; tests/test_ui.py TestLabel; data/raw/uk-cofid-2021 user guide PDF.

Review points for Elliot: "mainly starch" read as more than half of CHO; maltose taken as given; whether NPM inputs should move to label conventions (not done; would change scores).
