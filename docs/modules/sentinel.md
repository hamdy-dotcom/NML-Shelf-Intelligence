# sentinel — single-product deep dive

## Purpose
Given a product (searched by name, image, or barcode), show everywhere it's sold online, at what prices, and how much ad activity is running behind it. This is the fastest-to-demo, highest-visibility feature — build it right after genome has usable matching so the team gets a working tool early.

## Inputs
- Text search (Arabic/English product name)
- Image search (upload a photo, resolve via genome's image matching)
- Barcode/GTIN lookup

## Output, per product
- All matched listings (from `Listing`, joined via `genome`'s `product_id`): store name, price, listing URL, last-seen date
- Price range across stores (min/max/median)
- Number of distinct stores currently listing it
- Active ad count and platforms (from `AdSignal`), for the resolved product
- Simple trend line: listing count and ad count over time (needs `orbit` history, not just latest snapshot)

## API shape (sketch — adjust to your framework)
```
GET /sentinel/search?q=<text>
GET /sentinel/search?image=<upload>
GET /sentinel/product/{product_id}
  -> { product, listings[], price_range, active_ad_count, ad_platforms[], trend }
```

## Acceptance criteria (Phase 1)
- [ ] Text search returns matched listings and price range for a resolved product
- [ ] Ad count/platform data displays for products with `AdSignal` history
- [ ] Arabic-language search works as the primary case, not a fallback
- [ ] Results clearly distinguish "resolved product" view (aggregated across stores) from "unresolved listing" view (a single listing genome hasn't matched yet)
