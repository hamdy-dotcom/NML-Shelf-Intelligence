# genome — product identity matching

## Purpose
Resolves the same physical product across every online listing of it, even when store, title, and photo all differ. This is the hardest and most important module — `sentinel`, `oracle`, `prism`, and `pulse` all depend on genome's output quality.

## Data model
```
Product (canonical)
  - id
  - canonical_name_ar, canonical_name_en
  - category, subcategory
  - gtin (nullable — expect most products to lack a reliable one)
  - primary_image_url
  - created_at, updated_at
```
`Listing.product_id` (from orbit) is set by genome once resolved.

## Matching pipeline — build and run in this order, do not skip steps

**1. GTIN exact match.**
If a listing exposes a parseable barcode, resolve immediately and skip the rest of the pipeline for that listing. Treat this as a shortcut for a minority of listings, not the primary path — most small and mid-size Saudi online sellers don't tag GTINs correctly or at all. Never design coverage assumptions around GTIN being present.

**2. Text embedding match.**
Multilingual embedding model, must handle Arabic well (this carries the most matching weight given inconsistent barcode usage). Embed `listing_title_raw`, compare via cosine similarity against canonical `Product.canonical_name_ar/en` in pgvector. Surface top-k candidates above a similarity threshold.

**3. Image embedding match.**
This is a **cross-store retrieval problem**, not shelf recognition: same physical product, but the photo comes from a different store's photography — different angle, background, watermark, sometimes a stock photo vs. a real one. Do not train or fine-tune this on shelf-photo datasets; that's a different domain and won't transfer well.

Fine-tuning data source: pairs/clusters of "same product, different store's listing image," sourced from confirmed genome matches and `ledger` corrections. Start with a pre-trained CLIP-family model, fine-tune once you have a meaningful set of confirmed pairs (don't wait for a large dataset to start — iterate).

**4. LLM rerank.**
For ambiguous top-k candidates from steps 2–3 (i.e., no single high-confidence match), pass text + image + price context to an LLM and get a final same/different call, with a short reason logged alongside the decision.

## Feedback loop
Every human correction made in `ledger` (confirming, rejecting, or re-linking a genome match) is a labeled training example. Feed these back into steps 2–4 periodically — this is how matching quality improves over time, and it's expected to start rough and get better, not to be perfect at launch.

## Acceptance criteria (Phase 1)
- [ ] GTIN matching resolves listings that have a barcode
- [ ] Text embedding matching resolves a representative sample of Arabic-titled listings into canonical products
- [ ] Ambiguous matches are queued for human review via `ledger`, not silently guessed
- [ ] Every resolved `Listing.product_id` is traceable to which pipeline step resolved it (for later quality auditing)

Image matching can lag behind text/GTIN matching in Phase 1 — get text-based resolution solid first, since it's the highest-coverage layer.
