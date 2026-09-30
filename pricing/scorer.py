"""
pricing/scorer.py
Weighted deal scoring algorithm (0-100) with transparent factor breakdown per Section 4.6.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pricing.config import (
    PENALTY_LOW_CONFIDENCE,
    PENALTY_SUSPICIOUS_DISCOUNT,
    WEIGHT_DROP_MAGNITUDE,
    WEIGHT_DROP_VELOCITY,
    WEIGHT_EFFECTIVE_PRICE,
    WEIGHT_HISTORICAL_POSITION,
    WEIGHT_SELLER_TRUST,
    get_deal_label,
)
from pricing.models import DealVerdict, DropMetrics, HistoricalMetrics, PriceObservation


class DealScorer:
    """Computes weighted deal scores with complete per-factor explainability."""

    def compute_score(
        self,
        product_name: str,
        current_obs: PriceObservation,
        history: HistoricalMetrics,
        drop_metrics: DropMetrics,
        suspicious_discount: bool = False,
        suspicious_reason: str | None = None,
    ) -> DealVerdict:
        factors: list[dict[str, Any]] = []
        penalties: list[dict[str, Any]] = []
        raw_score = 0.0

        # 1. Historical Position Score (Max 40 pts)
        curr_p = current_obs.price
        if history.lowest_all_time > Decimal("0.00"):
            if curr_p <= history.lowest_all_time:
                hist_score = WEIGHT_HISTORICAL_POSITION
                hist_note = "At all-time low price!"
            elif curr_p <= history.lowest_30d:
                hist_score = WEIGHT_HISTORICAL_POSITION * 0.85
                hist_note = "At 30-day low price"
            elif history.median_30d > Decimal("0.00") and curr_p < history.median_30d:
                ratio = float((history.median_30d - curr_p) / history.median_30d)
                hist_score = min(WEIGHT_HISTORICAL_POSITION * 0.7, WEIGHT_HISTORICAL_POSITION * (ratio * 2.0))
                diff = history.median_30d - curr_p
                hist_note = f"₹{diff:,.2f} below 30-day median"
            else:
                hist_score = 5.0
                hist_note = "Above recent median price"
        else:
            hist_score = 20.0
            hist_note = "Initial price tracking observation"

        raw_score += hist_score
        factors.append({
            "name": "historical_position",
            "score": round(hist_score, 1),
            "max": WEIGHT_HISTORICAL_POSITION,
            "note": hist_note,
        })

        # 2. Drop Magnitude Score (Max 25 pts)
        drop_pct = drop_metrics.absolute_drop_pct
        if drop_pct >= 20.0:
            mag_score = WEIGHT_DROP_MAGNITUDE
        elif drop_pct > 0:
            mag_score = min(WEIGHT_DROP_MAGNITUDE, WEIGHT_DROP_MAGNITUDE * (drop_pct / 20.0))
        else:
            mag_score = 0.0

        raw_score += mag_score
        factors.append({
            "name": "drop_magnitude",
            "score": round(mag_score, 1),
            "max": WEIGHT_DROP_MAGNITUDE,
            "note": f"{drop_pct:.1f}% price reduction",
        })

        # 3. Drop Velocity Score (Max 10 pts)
        vel = drop_metrics.drop_velocity
        if vel >= 5.0:  # >= 5% drop per hour
            vel_score = WEIGHT_DROP_VELOCITY
            vel_note = f"Rapid drop of {vel:.1f}%/hour"
        elif vel > 0:
            vel_score = min(WEIGHT_DROP_VELOCITY, WEIGHT_DROP_VELOCITY * (vel / 5.0))
            vel_note = f"Drop velocity {vel:.1f}%/hour"
        else:
            vel_score = 0.0
            vel_note = "Steady price trend"

        raw_score += vel_score
        factors.append({
            "name": "velocity",
            "score": round(vel_score, 1),
            "max": WEIGHT_DROP_VELOCITY,
            "note": vel_note,
        })

        # 4. Effective Price Score (Max 15 pts)
        discounts = current_obs.total_discounts
        if curr_p > Decimal("0.00") and discounts > Decimal("0.00"):
            disc_pct = float((discounts / curr_p) * Decimal("100"))
            eff_score = min(WEIGHT_EFFECTIVE_PRICE, WEIGHT_EFFECTIVE_PRICE * (disc_pct / 15.0))
            eff_note = f"Stackable savings of ₹{discounts:,.2f}"
        else:
            eff_score = 0.0
            eff_note = "No extra stackable coupons or card offers"

        raw_score += eff_score
        factors.append({
            "name": "effective_price",
            "score": round(eff_score, 1),
            "max": WEIGHT_EFFECTIVE_PRICE,
            "note": eff_note,
        })

        # 5. Seller Trust Score (Max 10 pts)
        rating = current_obs.seller_rating
        if rating is not None and rating > 0:
            trust_score = min(WEIGHT_SELLER_TRUST, WEIGHT_SELLER_TRUST * (rating / 5.0))
            trust_note = f"{rating:.1f}★ rated seller"
        else:
            trust_score = WEIGHT_SELLER_TRUST * 0.7
            trust_note = f"Fulfilled by {current_obs.source.capitalize()}"

        raw_score += trust_score
        factors.append({
            "name": "seller_trust",
            "score": round(trust_score, 1),
            "max": WEIGHT_SELLER_TRUST,
            "note": trust_note,
        })

        # 6. Apply Penalties
        if suspicious_discount:
            raw_score -= PENALTY_SUSPICIOUS_DISCOUNT
            penalties.append({
                "name": "suspicious_discount",
                "penalty": PENALTY_SUSPICIOUS_DISCOUNT,
                "note": suspicious_reason or "Artificially inflated MRP detected",
            })

        if history.confidence == "low":
            raw_score -= PENALTY_LOW_CONFIDENCE
            penalties.append({
                "name": "low_confidence",
                "penalty": PENALTY_LOW_CONFIDENCE,
                "note": f"Limited history data ({history.observation_count} observations)",
            })

        final_score = max(0.0, min(100.0, raw_score))
        label = get_deal_label(final_score)

        return DealVerdict(
            product_name=product_name,
            deal_score=round(final_score, 0),
            label=label,
            factors=factors,
            penalties=penalties,
            confidence=history.confidence,
            suspicious_discount=suspicious_discount,
            suspicious_reason=suspicious_reason,
        )
