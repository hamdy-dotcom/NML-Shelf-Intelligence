# ledger — human-in-the-loop decision log

## Purpose
Every AI-generated recommendation (a genome match, an oracle product pick, a prism price) is shown to a human with its evidence, and approved/edited/rejected. This is the system's compounding asset: it's what trains genome, oracle, and prism over time, and it's the one thing no competitor can replicate just by buying the same data sources.

Start capturing decisions from day one — even before oracle/prism exist, log manual matching corrections and any manual shelf/price decisions the team makes, so there's no gap in the training data.

## Data model
```
Recommendation
  - id
  - type ("genome_match" | "oracle_pick" | "prism_price")
  - shelf_slot_id (nullable — genome matches aren't tied to a shelf slot)
  - product_id
  - listing_id (for genome_match type)
  - recommended_value (product_id for oracle, price for prism, match confirmation for genome)
  - reasoning_text (LLM-generated, plain language — required, never blank)
  - evidence_json (ad counts, listing counts, price range, cluster info — whatever drove the recommendation)
  - status ("pending" | "approved" | "rejected" | "edited")
  - edited_value (nullable — what the human changed it to, if status = "edited")
  - reviewed_by, reviewed_at
  - created_at
```

## UI requirements
- Every item in the review queue shows: the recommendation, the plain-language reason, and the evidence — never a bare score or a bare "yes/no" with no context.
- Approve / Reject / Edit actions, all logged with who and when.
- Reviewers should be able to filter/sort the queue (by type, by store, by confidence, by date).

## Why this matters more than it looks
- `genome` retraining source: every match confirmation/correction is a labeled pair.
- `oracle` retraining source: every approved/rejected product pick is training signal for moving from weighted-score to learned ranking.
- `prism` retraining source: every approved/edited price recommendation refines the perceived-value pricing model.

## Acceptance criteria (Phase 1)
- [ ] Every genome match below a high-confidence threshold lands in the review queue, not auto-applied silently
- [ ] Approve/reject/edit actions are logged with reviewer identity and timestamp
- [ ] Reasoning text and evidence are always present — no recommendation ships without them
- [ ] Data is queryable for later retraining (i.e., not just a UI log, a real structured table)
