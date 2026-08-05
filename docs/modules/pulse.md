# pulse — trend alerts

## Purpose
Flags products whose online momentum is crossing a threshold, so the team can act before a competitor's offline buyer does. Cheap to build once `orbit` has historical data — can be built in parallel with `atlas`/`prism`.

## Trigger conditions (start with these, tune thresholds with real data)
- Ad count spike: `AdSignal.ad_count_active` for a product rises sharply over a defined window
- Listing count spike: number of distinct stores listing a resolved product rises sharply
- Coordinated price drop: multiple stores drop price on the same resolved product within a short window
- Forward-looking search trend: rising interest in Google Trends / Shopping Trends topic data for the product's category, ideally using forward-prediction data where available (e.g., 13-week-ahead topic trend predictions) rather than only historical search volume

## Output
- Push/notify the team when a threshold is crossed, with the product, the specific signal that triggered it, and a link to `sentinel`'s deep-dive view for that product.
- Log every alert (even ones the team ignores) — useful later for tuning thresholds and, eventually, feeding back into `oracle`.

## Acceptance criteria (Phase 1)
- [ ] At least one trigger condition (ad count spike or listing count spike) is live and generating alerts from real `orbit` history
- [ ] Alerts link directly to the relevant `sentinel` product view
- [ ] Thresholds are configurable, not hardcoded
