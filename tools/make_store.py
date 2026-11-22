"""Generates a deterministic 100-SKU store for local testing."""
import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CATALOGUE = {
    "footwear": {
        "brands": ["Solecraft", "Northline", "Vayu", "Trailmark"],
        "items": ["Runner", "Court", "Trail", "Slip-on", "Hiker", "Trainer"],
        "price": (1800, 6500),
    },
    "apparel": {
        "brands": ["Kora", "Meridian", "Northline"],
        "items": ["Overshirt", "Tee", "Hoodie", "Chinos", "Jacket", "Shorts"],
        "price": (700, 4200),
    },
    "electronics": {
        "brands": ["Volt", "Aurex", "Kite"],
        "items": ["Earbuds", "Powerbank", "Charger", "Speaker", "Keyboard", "Mouse"],
        "price": (900, 8900),
    },
    "home": {
        "brands": ["Terra", "Hearth"],
        "items": ["Lamp", "Kettle", "Rug", "Shelf", "Mug Set", "Throw"],
        "price": (500, 5200),
    },
    "sports": {
        "brands": ["Stryke", "Vayu"],
        "items": ["Yoga Mat", "Bottle", "Duffel", "Grip Tape", "Band Set"],
        "price": (400, 3400),
    },
    "accessories": {
        "brands": ["Aurex", "Kite", "Kora"],
        "items": ["Sling Bag", "Cap", "Belt", "Wallet", "Watch Strap"],
        "price": (350, 2900),
    },
}

COLOURS = ["black", "white", "navy", "olive", "grey", "sand"]

MIN_MARGIN = {
    "footwear": 0.22,
    "apparel": 0.30,
    "electronics": 0.12,
    "home": 0.25,
    "sports": 0.20,
    "accessories": 0.35,
}


def main() -> None:
    rng = random.Random(20261122)
    rows = []
    sku = 1001
    per_cat = 100 // len(CATALOGUE)
    for cat, spec in CATALOGUE.items():
        for _ in range(per_cat):
            lo, hi = spec["price"]
            price = rng.randrange(lo, hi, 50)
            m = MIN_MARGIN[cat]
            margin = rng.uniform(m + 0.06, min(m + 0.26, 0.52))
            cost = round(price * (1 - margin))
            rows.append({
                "sku": f"SKU-{sku}",
                "category": cat,
                "brand": rng.choice(spec["brands"]),
                "name": f"{rng.choice(spec['items'])} {rng.choice(COLOURS).title()}",
                "list_price": price,
                "cost": cost,
                "stock": rng.choice([0, 1, 2, 3, 5, 8, 12, 20, 35]),
            })
            sku += 1
    with (ROOT / "store.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} SKUs")


if __name__ == "__main__":
    main()
