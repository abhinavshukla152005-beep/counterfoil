"""Store data and the pricing policy that bounds every offer."""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Product:
    sku: str
    category: str
    brand: str
    name: str
    list_price: int
    cost: int
    stock: int


class Store:
    def __init__(self, products: dict[str, Product]):
        self._products = products

    @classmethod
    def load(cls, path: str | Path) -> "Store":
        products = {}
        with Path(path).open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                p = Product(
                    sku=row["sku"],
                    category=row["category"],
                    brand=row["brand"],
                    name=row["name"],
                    list_price=int(row["list_price"]),
                    cost=int(row["cost"]),
                    stock=int(row["stock"]),
                )
                products[p.sku] = p
        return cls(products)

    def get(self, sku: str) -> Product | None:
        return self._products.get(sku)

    def all(self) -> list[Product]:
        return list(self._products.values())

    def by_category(self, category: str) -> list[Product]:
        return [p for p in self._products.values() if p.category == category]


class Policy:
    def __init__(self, data: dict):
        self.data = data
        self.max_rounds = int(data["max_rounds"])
        self.bundle = {int(k): float(v) for k, v in data["bundle_discount"].items()}
        self.per_round_step = float(data["concession"]["per_round_step"])
        self.gap_share = float(data["concession"].get("gap_share", 0.5))
        self.total_cap = float(data["concession"]["total_cap"])

    @classmethod
    def load(cls, path: str | Path) -> "Policy":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    def _cat(self, product: Product) -> dict:
        return self.data["categories"][product.category]

    def margin_floor(self, p: Product) -> int:
        m = float(self._cat(p)["min_margin"])
        return math.ceil(p.cost / (1 - m))

    def discount_floor(self, p: Product) -> int:
        d = float(self._cat(p)["max_discount"])
        return math.ceil(p.list_price * (1 - d))

    def floor_unit(self, p: Product) -> int:
        return max(self.margin_floor(p), self.discount_floor(p))

    def bundle_rate(self, distinct_lines: int) -> float:
        return self.bundle.get(distinct_lines, 0.0)

    def violation(self, p: Product, unit_price: int, qty: int) -> str | None:
        if qty <= 0:
            return "non_positive_quantity"
        if qty > p.stock:
            return "insufficient_stock"
        if unit_price < self.floor_unit(p):
            if unit_price < self.margin_floor(p):
                return "below_min_margin"
            return "over_max_discount"
        return None
