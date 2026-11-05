---
type: feature-assessment
status: specified-not-built
area: shelfscale
created: 2026-11-05
updated: 2026-11-05
---

# Picture-based assessment: verdict and safe design

Elliot asked whether a user can photograph a product to assess it. Short answer: yes, and it is a normal pattern in this category, but a photograph is an intake method, not evidence. The picture's job is to identify the product and capture its label. The assessment still comes from defensible data: the manufacturer's data behind the barcode, or the label values the photo captured, checked and confirmed.

## The three stages, in order of trust

### Stage A: barcode first (build first)
The photo or camera scan reads the GTIN from the EAN/UPC barcode. Standard on-device libraries do this well offline (Google's ML Kit barcode scanning reads EAN-13, EAN-8, UPC-A/E and QR formats on the device, in any orientation). The GTIN then resolves through the normal evidence order: manufacturer data, licensed catalogue, official generic match. A GS1 Digital Link QR can also resolve directly to the brand's declared nutrition information.

Trust level: high. The barcode identifies the exact product and variant, including pack size, which is where lookalike products usually go wrong.

### Stage B: label capture (build second)
When there is no barcode match, the user photographs the back-of-pack nutrition table and ingredients list. OCR extracts candidate values; the system then:

- checks the numbers against each other (energy versus macronutrients, per-100 g versus per-portion columns, salt versus sodium);
- shows the extracted table to the user for confirmation or correction;
- stores the confirmed values as a label transcription, with the photo as its evidence, credited to that product only.

Trust level: medium, and only with the confirmation step. OCR misreads decimals and similar digits; an unconfirmed OCR value never enters the data.

### Stage C: loose and unpackaged items (assist only)
A photo of loose produce or a deli item can suggest candidate identities (for example, banana, Cavendish-type, raw). It cannot settle variety, preparation, or weight from the image alone: portion size from a photo is unreliable without a scale or a known reference object in frame. So Stage C returns candidate matches and asks for the weight or a weighed sample basis, then applies the loose-item method in SPEC.md section 8. The output is labelled an estimate with its basis, as always.

Trust level: assistive. The photo narrows the match; it never makes it.

## Hard rules

- A picture never creates a nutrient value. It identifies, or it transcribes a label under confirmation.
- Front-of-pack photos alone are not enough to assess: no full table, no score; the flow asks for the back of pack.
- Similar variants (flavours, fat levels, pack sizes) must be separated by the barcode or by explicit user confirmation of the variant.
- Images are processed on device for barcode reading where possible. Uploaded label photos are retained only with the organisation's opt-in, and are evidence for that product's transcription, nothing else.
- Reformulation risk: a sharp photo of an old pack is still an old pack. Label transcriptions carry the capture date, and a newer manufacturer source supersedes them.

## Evaluation before launch

Each stage ships only after it passes a gold-set test: a photographed set of real products (including glare, creased packs, multipacks and lookalikes) where barcode accuracy, OCR field accuracy and variant separation are measured and reported. Stage C ships only with its estimate labelling, never as a silent score.

## Why universities and retailers care

- Retailers can audit shelves and supplier samples with the same flow their suppliers use, and every photo-backed value arrives with its evidence attached.
- Universities get a field-data collection tool for retail surveys (the FSA's own surveillance work is sample-based) where students capture products and supervisors review transcriptions in a queue, instead of typing labels into spreadsheets.
