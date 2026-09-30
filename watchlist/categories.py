"""
watchlist/categories.py
Automated category inference engine for catalog products.
"""

from __future__ import annotations

import re

CATEGORY_RULES: list[tuple[str, re.Pattern]] = [
    (
        "Mobiles & Tablets",
        re.compile(
            r"\b(iphone|ipad|galaxy|smartphone|mobile|tablet|oneplus|redmi|realme|vivo|oppo|pixel|poco|iqoo)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Electronics & Laptops",
        re.compile(
            r"\b(macbook|laptop|notebook|desktop|monitor|keyboard|mouse|gpu|ssd|hard drive|intel|ryzen|nvidia|ram)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Audio & Wearables",
        re.compile(
            r"\b(headphone|headphones|headset|earbud|earbuds|earphone|airpods|neckband|bluetooth|speaker|soundbar|smartwatch|watch|boat|noise|boult|sony wh)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "TV & Appliances",
        re.compile(
            r"\b(tv|television|oled|qled|refrigerator|fridge|washing machine|air conditioner|ac|microwave|geyser|purifier)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "Fashion & Apparel",
        re.compile(
            r"\b(shoe|shoes|sneakers|t-shirt|tshirt|shirt|jeans|trousers|dress|jacket|hoodie|nike|adidas|puma|u\.s\. polo|levis)\b",
            re.IGNORECASE,
        ),
    ),
]


def infer_category(title: str) -> str:
    """Infer category from product title."""
    if not title:
        return "General"
    for cat_name, pattern in CATEGORY_RULES:
        if pattern.search(title):
            return cat_name
    return "General"
