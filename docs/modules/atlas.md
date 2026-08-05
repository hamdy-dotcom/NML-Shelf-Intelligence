# atlas — store cluster map

## Purpose
Groups physical store branches (بندة/Panda, العثيم/Othaim, etc.) into clusters by economic geography and shopper behavior. Feeds two different downstream questions: `oracle` uses clusters to decide *what* to stock, `prism` uses the same clusters to decide *what to charge* — same cluster, two different consumers of it.

## Data model
```
Store
  - id
  - name, chain ("panda" | "othaim" | ...)
  - branch_location (lat/lon or region code)
  - cluster_id (fk -> StoreCluster)

StoreCluster
  - id
  - label (human-readable, e.g. "Riyadh VIP", "Jeddah mass-market")
  - income_tier
  - footfall_tier
  - region_source (GASTAT region code or equivalent)
  - notes
```

## Clustering inputs
- **GASTAT regional/retail statistics** (real government data — income levels, population density, regional retail revenue growth) as the primary quantitative input. Do not guess or hand-wave cluster assignments; use published regional indicators as the starting point.
- Store-level signals as they become available: branch size, foot traffic estimates, local price sensitivity observed via `orbit`/`prism` outcomes over time.
- Manual tagging/override capability — the team should be able to correct a cluster assignment (e.g., "this branch is in a genuinely VIP micro-area GASTAT's regional average doesn't capture") and have that stick.

## Key behavior
A cluster isn't just a label — it needs to carry enough structured signal (income_tier, footfall_tier) that `prism` can use it directly in a pricing formula, and `oracle` can use it directly as a category-gap/relevance feature.

## Acceptance criteria (Phase 1)
- [ ] Every `Store` has a `cluster_id` assigned, seeded from GASTAT regional data
- [ ] Cluster assignments are manually overridable by the team, with the override logged
- [ ] `income_tier` and `footfall_tier` (or equivalent structured fields) are queryable per cluster — not just a free-text label
