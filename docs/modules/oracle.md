# oracle — the shelf recommender

## Purpose
Given an open shelf slot (store, category, size), rank candidate products by predicted offline sell-through. Build this last — it needs `genome`, `atlas`, and ideally some `ledger` history to be worth building well.

## Data model
```
ShelfSlot
  - id
  - store_id
  - category
  - open_date
  - status ("open" | "filled")
```
Recommendations are written to `ledger.Recommendation` with `type = "oracle_pick"`.

## Scoring approach — two phases, do not skip to phase 2 early

**Phase 1 (launch): weighted scoring, no ML.**
Score candidate products for a given `ShelfSlot` using explicit, inspectable weights over:
- Online sales/order velocity (from `orbit`, via genome-resolved products)
- Ad intensity trend (from `AdSignal`)
- Category gap in that store's `atlas` cluster (is this category under-represented there relative to similar clusters?)
- Price fit (does the product's price range make sense for this store's cluster, cross-checked against `prism`)

Keep the weights configurable and visible — the team should be able to see *why* a product scored the way it did, in the `reasoning_text` shipped to `ledger`.

**Phase 2 (later): learned ranking.**
Once `ledger` has a meaningful volume of approve/reject/edit outcomes on oracle picks, retrain toward a learned-ranking model using that history as labels. Don't attempt this before real outcome data exists — a model trained on synthetic or assumed labels will encode nothing useful.

## Output requirement
Every recommendation must include:
- Ranked candidate list (not just a single pick) — the reviewer should see alternatives
- `reasoning_text`: plain-language explanation pulling from the evidence (e.g., "ad activity for this SKU is up 40% this month, and this category is under-represented in this store's cluster compared to similar branches")
- `evidence_json`: the raw numbers behind the reasoning

## Acceptance criteria (Phase 1)
- [ ] Given an open `ShelfSlot`, oracle returns a ranked candidate list with scores and reasoning
- [ ] Scoring weights are configurable, not hardcoded magic numbers buried in logic
- [ ] Every recommendation lands in `ledger` for review before being treated as final
