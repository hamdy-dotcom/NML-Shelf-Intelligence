"""
Prism pricing logic — cluster_adjustment table and formula.

Keep this module simple and inspectable: the team needs to be able to see and
challenge every number here. No black boxes. When real ledger approve/reject
volume exists, replace the heuristic values below with empirically fitted ones.

Formula:
    recommended_price = base_price * (1 + cluster_adjustment)
    cluster_adjustment = tier_base * category_elasticity_multiplier
"""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

# ---------------------------------------------------------------------------
# Adjustment table  (income_tier × footfall_tier → base factor)
# ---------------------------------------------------------------------------
# These are starting heuristics informed by general retail pricing theory:
#   high-income + high-footfall → strongest markup room
#   mid-income + mid-footfall  → price at market (0% adjustment)
#   low-income                 → price below market to stay competitive
#
# NOT calibrated against real sales data. Replace values as ledger data accrues.

TIER_ADJUSTMENTS: dict[str, dict[str, float]] = {
    "high": {"high": 0.15, "mid": 0.12, "low": 0.10},
    "mid":  {"high": 0.05, "mid": 0.00, "low": -0.03},
    "low":  {"high": -0.05, "mid": -0.08, "low": -0.10},
}

# ---------------------------------------------------------------------------
# Category elasticity multipliers
# ---------------------------------------------------------------------------
# Staple/commodity categories have lower price elasticity — customers are price-
# sensitive and will switch brands or stores. Discretionary/lifestyle categories
# tolerate more markup because the purchase is less frequent and more aspirational.
#
# "unknown" is the conservative default when the product has no category set.

CATEGORY_ELASTICITY: dict[str, float] = {
    "staple":        0.5,
    "commodity":     0.5,
    "discretionary": 1.0,
    "lifestyle":     1.0,
    "unknown":       0.5,
}

# Tier values we recognise; anything else falls back to "mid" / "unknown".
_VALID_TIERS = {"high", "mid", "low"}


# ---------------------------------------------------------------------------
# Core calculation
# ---------------------------------------------------------------------------

@dataclass
class PriceResult:
    base_price: Decimal
    tier_base_adjustment: float      # from TIER_ADJUSTMENTS lookup
    elasticity_multiplier: float     # from CATEGORY_ELASTICITY lookup
    cluster_adjustment: float        # tier_base * elasticity_multiplier
    recommended_price: Decimal
    currency: str
    reasoning_text: str
    evidence: dict


def compute_price(
    base_price: Decimal,
    income_tier: str,
    footfall_tier: str,
    category: str | None,
    cluster_label: str,
    listing_count: int,
    currency: str = "SAR",
) -> PriceResult:
    """
    Apply the prism formula and build the reasoning + evidence payload.
    All inputs are validated/normalised before the formula runs.
    """
    income_tier = income_tier if income_tier in _VALID_TIERS else "mid"
    footfall_tier = footfall_tier if footfall_tier in _VALID_TIERS else "mid"

    cat_key = (category or "unknown").lower()
    if cat_key not in CATEGORY_ELASTICITY:
        cat_key = "unknown"

    tier_base = TIER_ADJUSTMENTS[income_tier][footfall_tier]
    elasticity = CATEGORY_ELASTICITY[cat_key]
    cluster_adjustment = round(tier_base * elasticity, 4)

    recommended = (base_price * Decimal(str(1 + cluster_adjustment))).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    adj_pct = round(cluster_adjustment * 100, 1)
    sign = "+" if adj_pct >= 0 else ""
    tier_pct = round(tier_base * 100, 0)
    tier_sign = "+" if tier_base >= 0 else ""

    reasoning = (
        f"Median online price across {listing_count} listing(s) is {currency} {base_price}. "
        f"Destination cluster '{cluster_label}' (income_tier={income_tier}, "
        f"footfall_tier={footfall_tier}): base tier adjustment is {tier_sign}{tier_pct:.0f}%, "
        f"scaled by {cat_key} category elasticity factor ({elasticity}×) "
        f"to a final adjustment of {sign}{adj_pct}%. "
        f"Recommended retail price: {currency} {recommended}."
    )

    evidence = {
        "base_price": str(base_price),
        "currency": currency,
        "listing_count": listing_count,
        "cluster_label": cluster_label,
        "income_tier": income_tier,
        "footfall_tier": footfall_tier,
        "category": cat_key,
        "tier_base_adjustment": tier_base,
        "elasticity_multiplier": elasticity,
        "cluster_adjustment": cluster_adjustment,
        "recommended_price": str(recommended),
    }

    return PriceResult(
        base_price=base_price,
        tier_base_adjustment=tier_base,
        elasticity_multiplier=elasticity,
        cluster_adjustment=cluster_adjustment,
        recommended_price=recommended,
        currency=currency,
        reasoning_text=reasoning,
        evidence=evidence,
    )
