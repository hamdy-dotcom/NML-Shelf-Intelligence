# orbit — live online radar

## Purpose
Continuously-refreshing database of online listings, prices, and ad presence across Salla-powered and other major KSA online stores. Every other module queries this as ground truth. Nothing else in the system works without this being reliable.

## Data model
```
Listing
  - id
  - product_id (nullable until genome resolves it)
  - store_name, store_url
  - listing_title_raw
  - listing_image_url
  - price
  - currency (always "SAR")
  - scraped_at
  - source ("salla_api" | "public_listing" | "manual")

AdSignal
  - id
  - product_id (nullable until genome resolves it)
  - listing_id (nullable — some ad signal won't map to a specific listing yet)
  - platform ("meta" | "tiktok" | "snap" | "google")
  - ad_count_active
  - observed_at
```

## Ingestion sources, in priority order
1. **Salla Partner API** (`api.salla.dev/admin/v2`, OAuth2 via Salla Partners) — primary structural source. Pull products, orders (for order-velocity proxy), branches, marketing/coupons on a schedule.
2. **Official ad transparency tools** — Meta Ad Library, TikTok Creative Center, Snap/Google Ads Transparency. Pull ad counts/presence for tracked products/brands on a schedule.
3. **Public listing pages** of other major KSA stores (Amazon.sa, Noon, other Salla-hosted merchant storefronts) — public page data only, no login-gated scraping.
4. GS1/GTIN lookups where a listing exposes a barcode — cheap enrichment, not a primary source.

## Scheduling
- Salla API and ad libraries: near-real-time is achievable and worth the cost — pull frequently (define interval based on API rate limits, but favor freshness).
- Public listing scraping: respect robots.txt and rate limits; this is a supplementary source, not the backbone — don't over-engineer scraping infra before the Salla pipeline is solid.

## Explicit exclusions
- No scraping behind login walls.
- No use of leaked, breached, or otherwise illegitimately obtained data, under any framing.
- No storefront scraping that violates a site's terms of service — prefer official APIs/partnerships wherever one exists.

## Acceptance criteria (Phase 1)
- [ ] Salla API pull runs on schedule and writes to `Listing`
- [ ] At least one ad transparency source writes to `AdSignal`
- [ ] Data freshness is visible/queryable (last `scraped_at`/`observed_at` per source)
- [ ] Duplicate listings from the same store/product aren't silently re-inserted — upsert logic in place
