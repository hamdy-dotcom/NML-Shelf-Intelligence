# prism — perceived-value pricing

## Purpose
Given a product and a specific shelf slot, recommend a price — conditioned on that shelf's store cluster (from `atlas`), not one national price per product. A VIP/high-income branch can justify a markup over the product's online price; a mass-market branch may need to stay at or below it. This is a first-class requirement, not an edge case — every price recommendation must factor in the destination store's cluster.

## Inputs
- Online price range for the product across stores (from `orbit`, via genome-resolved `Product`)
- `atlas` cluster of the destination `Store`/`ShelfSlot` (income_tier, footfall_tier)
- Category-level price elasticity (start with simple heuristics — e.g., staple/commodity categories get less markup room than discretionary/lifestyle categories — refine with real data over time)

## Pricing logic (starting formula — adjust as real data comes in)
```
base_price = median(online listing prices for the resolved product)
cluster_adjustment = f(cluster.income_tier, cluster.footfall_tier, category)
recommended_price = base_price * (1 + cluster_adjustment)
```
Keep `cluster_adjustment` as an explicit, inspectable factor — not a black box. The team needs to be able to see and challenge why a price was pushed up or down for a given store.

## Output requirement
Every price recommendation, like oracle's, ships with:
- `reasoning_text`: e.g., "median online price is 45 SAR; this branch is in a high-income, high-footfall cluster where similar categories carry a 10-15% markup — recommending 51 SAR"
- `evidence_json`: base price, cluster tier, category elasticity assumption used

Written to `ledger.Recommendation` with `type = "prism_price"`.

## Acceptance criteria (Phase 1)
- [ ] Given a product + shelf slot, prism returns a recommended price with reasoning and evidence
- [ ] The same product recommended for two different-cluster shelf slots produces genuinely different prices, not the same number twice
- [ ] `cluster_adjustment` logic is configurable/inspectable, not hardcoded per-store special cases
