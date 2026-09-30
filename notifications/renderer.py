"""
notifications/renderer.py
Single source of truth for formatting deal alert messages across all channels.
Guarantees consistent layout, transparent factors, and mandatory consumer caveats.
"""

from __future__ import annotations

from notifications.models import AlertPayload

RULE_HEADINGS: dict[str, str] = {
    "TARGET_HIT": "🎯 *TARGET PRICE HIT!*",
    "PRICE_DROP": "📉 *PRICE DROP DETECTED!*",
    "BIG_DEAL": "💥 *MAJOR PRICE DROP (15%+ OFF)!*",
    "ALL_TIME_LOW": "🏆 *ALL-TIME LOW PRICE!*",
    "STRONG_DEAL": "🔥 *STRONG DEAL DETECTED!*",
    "COUPON_ALERT": "🎟️ *NEW COUPON AVAILABLE!*",
}


class MessageRenderer:
    """Builds channel-agnostic, markdown-formatted deal alert text."""

    @staticmethod
    def render(payload: AlertPayload) -> str:
        """Render complete alert message including explainability block and caveats."""
        header = RULE_HEADINGS.get(payload.rule, "🔔 *PRICE ALERT!*")
        store = payload.platform.capitalize()

        # 1. Price Change Breakdown
        price_diff = payload.drop_amount
        pct_diff = payload.drop_pct

        price_section = [
            f"💰 *Previous:* ~₹{payload.previous_price:,.2f}~",
            f"🏷️ *Current Price:* ₹{payload.current_price:,.2f} *(Save ₹{price_diff:,.2f} / -{pct_diff:.1f}%)*",
        ]

        # 2. Effective price and stackable discounts
        discounts = []
        if payload.coupon:
            discounts.append(f"• Coupon Discount: -₹{payload.coupon:,.2f}")
        if payload.bank_offer:
            discounts.append(f"• Bank/Card Offer: -₹{payload.bank_offer:,.2f}")

        if discounts:
            price_section.append("✨ *Stackable Offers:*")
            price_section.extend(discounts)

        if payload.effective_price < payload.current_price:
            price_section.append(f"🔥 *Net Effective Price:* ₹{payload.effective_price:,.2f}")

        # 3. Deal Score & Factors (if present)
        score_section = []
        if payload.deal_score is not None:
            score_section.append(f"⭐ *Deal Score:* {payload.deal_score:.0f}/100")
            for factor in payload.factors[:3]:
                note = factor.get("note", "")
                name = factor.get("name", "").replace("_", " ").title()
                score_section.append(f"  └ {name}: {note}")

        # 4. Conditions & Caveats
        condition_lines = []
        if payload.condition_notes:
            condition_lines.append("⚠️ *Offer Conditions:*")
            for note in payload.condition_notes:
                condition_lines.append(f"• {note}")

        caveat = (
            "ℹ️ *Disclaimer:* Prices & offers change rapidly. Score is an automated heuristic, "
            "not a purchase guarantee or financial advice."
        )

        blocks = [
            f"{header}\n",
            f"📦 *{payload.product_name}*",
            f"🏪 *Store:* {store}",
            "\n".join(price_section),
        ]

        if score_section:
            blocks.append("\n".join(score_section))

        if condition_lines:
            blocks.append("\n".join(condition_lines))

        blocks.append(f"🔗 [View Product on {store}]({payload.canonical_url})")
        blocks.append(caveat)

        return "\n\n".join(blocks)
