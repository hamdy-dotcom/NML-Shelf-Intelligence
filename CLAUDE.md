# NML Shelf Intelligence — Project Context

This file is loaded automatically by Claude Code as persistent project context. Detailed specs for each module live in `docs/modules/`. Read the relevant module doc before working on that module — don't rely on this file alone for implementation detail.

---

## 0. What this system is

NML moves products sold online into offline retail shelf space (بندة/Panda, العثيم/Othaim, and other partner chains) in Saudi Arabia, in partnership with Salla. Another team secures shelf space; this system decides **which product goes on it** and **at what price**, using online sales/ad signal as the leading indicator, with a mandatory human approval step on every recommendation before it's acted on.

**Market**: Saudi Arabia only.
**Language**: Arabic-first for UI, product matching, and search — English is secondary, not primary. Do not build Arabic support as an add-on after the fact; it's the base case.
**Currency**: SAR throughout.

---

## 1. Module index

Read each module's file in `docs/modules/` before implementing it.

| Module | File | One-line purpose |
|---|---|---|
| orbit | `docs/modules/orbit.md` | Live ingestion + database of online listings, prices, ad presence |
| genome | `docs/modules/genome.md` | Resolves the same product across different stores/listings/photos |
| sentinel | `docs/modules/sentinel.md` | Single-product lookup: where it's sold, prices, ad activity, trend |
| ledger | `docs/modules/ledger.md` | Human review/approval queue for every AI recommendation — also the training data source |
| atlas | `docs/modules/atlas.md` | Groups physical stores into clusters by economic geography and shopper behavior |
| oracle | `docs/modules/oracle.md` | Given an open shelf slot, ranks candidate products to fill it |
| prism | `docs/modules/prism.md` | Given a product + shelf slot, recommends a price based on that location's perceived value |
| pulse | `docs/modules/pulse.md` | Momentum alerts — flags products trending up before they peak |

## 2. Build order (do not reorder without reason)

1. **orbit** — nothing else works without live data
2. **genome** — product resolution is the foundation everything else queries
3. **sentinel** — fastest visible win, validates orbit+genome data quality early
4. **ledger** — start capturing human decisions from day one, even before oracle/prism exist (log manual decisions if needed) — this is the compounding asset, don't delay it
5. **atlas** — store clustering, needed before prism and useful for oracle
6. **prism** — pricing, needs atlas clusters
7. **pulse** — cheap once orbit has history; low dependency risk, can be built in parallel with atlas/prism
8. **oracle** — build last. Launch as a simple weighted-score system first; do not attempt a learned-ranking model until ledger has real approve/reject volume to train on

## 3. Tech stack (defaults — deviate only with a clear reason, and note the reason in code comments)

- **Relational store**: Postgres — `Product`, `Listing`, `Store`, `ShelfSlot`, `Recommendation`, `AdSignal` and all structured data
- **Vector store**: pgvector (start here — avoid standing up a separate vector DB like Qdrant/Milvus until Postgres genuinely can't keep up) — product text + image embeddings for genome
- **Time-series / high-volume append data**: if `AdSignal` and price-history volume grows past what Postgres handles comfortably, move to ClickHouse — not needed at MVP scale
- **Embeddings**: multilingual text embedding model (must handle Arabic well) for genome step 2; CLIP-family image embedding model, fine-tuned per `genome.md` instructions, for genome step 3
- **LLM use**: reranking ambiguous genome matches, and generating plain-language reasoning text for oracle/prism recommendations — never surface a bare numeric score to a human reviewer without a reason attached

## 4. Data sources — three tiers, treat them differently

**Structural (build the real pipeline around this):**
- Salla Partner API (`api.salla.dev/admin/v2`, OAuth2) — products, orders, branches, marketing data

**Base/free layer (wire in early, low effort, but this is not your differentiation):**
- Meta Ad Library, TikTok Creative Center, Snap/Google ad transparency tools — ad signal
- Google Trends / Google Shopping Trends topic API — forward-looking demand signal, feeds `pulse`
- GASTAT regional/retail statistics — feeds `atlas` clustering
- GS1 lookups — GTIN resolution shortcut in `genome`, covers a minority of listings, use opportunistically
- Open Food Facts / Open Products Facts — free seed catalog data where barcodes exist

**Proprietary (this is the actual product — invest here):**
- Long-tail coverage of small Salla merchants that commercial ad-spy tools don't bother tracking
- `genome`'s cross-store product resolution pipeline
- `ledger`'s accumulated dataset of human approve/reject/edit decisions

## 5. Non-negotiable requirements

- Every AI-generated recommendation (from `oracle` or `prism`) must ship with an evidence payload (what data drove it) and a plain-language reason — never a bare score in any UI.
- No scraping behind login walls, no use of leaked/breached data sources, ever. Ad signal comes from official transparency tools; storefront data comes from Salla's partner terms or public listing pages only.
- Every recommendation's outcome (approved/rejected/edited, and by whom) must be logged in `ledger` — this is required infrastructure from day one, not a later addition.
- Arabic product names/titles must be handled as first-class input everywhere text matching happens, not transliterated or treated as a fallback case.

## 6. Repo structure

```
/orbit          # ingestion services, scheduled jobs
/genome         # matching pipeline (GTIN, text embed, image embed, LLM rerank)
/sentinel       # single-product lookup API + UI
/ledger         # review queue UI + decision logging
/atlas          # clustering jobs + store cluster API
/oracle         # shelf recommendation engine
/prism          # pricing engine
/pulse          # trend/alerting jobs
/shared         # shared DB models, auth, embedding clients
/docs/modules   # detailed per-module specs — read before implementing
```
