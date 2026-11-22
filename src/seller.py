"""Policy-bounded seller agent.

Design rule: the seller never reads the buyer's free text. A counter only
carries numbers (sku/qty/unit_price), and every number the seller emits is
derived from store.csv through policy.json. Text therefore cannot move a
price, which makes claim injection (fake competitor quotes, fake manager
approval, fake urgency, "ignore your policy") structurally impossible rather
than something a prompt has to defend against.

Concessions are earned. The seller only reduces its ask after the buyer
actually improves on its previous offer, and only by the smaller of a fixed
per-round step and a share of the remaining gap. A buyer that repeats its
last number sees the price hold.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .catalog import Policy, Product, Store

MAX_LINES = 20
MAX_QTY = 500


def money(x: float) -> int:
    return int(math.floor(x + 0.5))


class InquiryError(ValueError):
    """Buyer sent something the seller cannot price."""


@dataclass
class Negotiation:
    store: Store
    policy: Policy
    buyer_id: str
    lines: list[tuple[Product, int]]
    unit: dict[str, int] = field(default_factory=dict)
    round: int = 1
    offer_seq: int = 0
    last_offer: dict | None = None
    best_buyer_total: int = 0
    closed: str | None = None  # "accepted" | "walked_away"
    final: dict | None = None
    dropped: list[dict] = field(default_factory=list)

    # ---------------------------------------------------------------- setup

    @classmethod
    def open(cls, store: Store, policy: Policy, inquiry: dict) -> "Negotiation":
        buyer_id = str(inquiry.get("buyer_id") or "anonymous")[:64]
        raw = inquiry.get("lines")
        if not isinstance(raw, list) or not raw:
            raise InquiryError("inquiry needs a non-empty lines list")
        if len(raw) > MAX_LINES:
            raise InquiryError(f"at most {MAX_LINES} lines per inquiry")

        lines: list[tuple[Product, int]] = []
        dropped: list[dict] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                raise InquiryError("every line must be an object")
            sku = str(item.get("sku") or "")
            try:
                qty = int(item.get("qty"))
            except (TypeError, ValueError):
                raise InquiryError(f"qty must be an integer for {sku!r}")
            if qty <= 0:
                raise InquiryError(f"qty must be positive for {sku!r}")
            if sku in seen:
                raise InquiryError(f"duplicate sku in inquiry: {sku!r}")
            seen.add(sku)

            product = store.get(sku)
            if product is None:
                dropped.append({"sku": sku, "reason": "unknown_sku"})
                continue
            if product.stock == 0:
                dropped.append({"sku": sku, "reason": "out_of_stock"})
                continue
            if qty > MAX_QTY:
                qty = MAX_QTY
            if qty > product.stock:
                dropped.append(
                    {"sku": sku, "reason": "qty_clamped", "requested": qty, "available": product.stock}
                )
                qty = product.stock
            lines.append((product, qty))

        if not lines:
            raise InquiryError("no requested line can be served from stock")
        neg = cls(store=store, policy=policy, buyer_id=buyer_id, lines=lines, dropped=dropped)
        neg._price_opening()
        return neg

    def _price_opening(self) -> None:
        rate = self.policy.bundle_rate(len(self.lines))
        for p, _ in self.lines:
            raw = p.list_price * (1.0 - rate)
            self.unit[p.sku] = max(self.policy.floor_unit(p), money(raw))

    # ------------------------------------------------------------ pricing

    def _bundle_rate(self) -> float:
        return self.policy.bundle_rate(len(self.lines))

    def ask_total(self) -> int:
        return sum(self.unit[p.sku] * q for p, q in self.lines)

    def floor_total(self) -> int:
        return sum(self.policy.floor_unit(p) * q for p, q in self.lines)

    def opening_total(self) -> int:
        rate = self.policy.bundle_rate(len(self.lines))
        total = 0
        for p, q in self.lines:
            total += max(self.policy.floor_unit(p), money(p.list_price * (1.0 - rate))) * q
        return total

    def min_total(self) -> int:
        capped = math.ceil(self.opening_total() * (1.0 - self.policy.total_cap))
        return max(self.floor_total(), capped)

    def _concede(self, rupees: int) -> None:
        """Remove `rupees` from the ask, one unit price at a time, largest headroom first."""
        remaining = rupees
        while remaining > 0:
            pick: tuple[str, int, int] | None = None
            for p, q in self.lines:
                head = self.unit[p.sku] - self.policy.floor_unit(p)
                if head > 0 and (pick is None or head > pick[1]):
                    pick = (p.sku, head, q)
            if pick is None:
                return
            sku, head, qty = pick
            take = min(head, max(1, remaining // qty))
            self.unit[sku] -= take
            remaining -= take * qty

    # ------------------------------------------------------------- emission

    def _claims(self) -> list[dict]:
        claims = [
            {"field": "bundle_discount", "value": round(self._bundle_rate(), 4)},
            {"field": "round", "value": self.round},
        ]
        for p, _ in self.lines:
            claims.append({"sku": p.sku, "field": "list_price", "value": p.list_price})
            claims.append({"sku": p.sku, "field": "stock", "value": p.stock})
        return claims

    def _note(self) -> str:
        units = sum(q for _, q in self.lines)
        return (
            f"Round {self.round} of {self.policy.max_rounds}. "
            f"{len(self.lines)} lines, {units} units. "
            f"Bundle {round(self._bundle_rate() * 100)} percent. "
            f"Stock checked against the store before this offer."
        )

    def _emit_offer(self) -> dict:
        self.offer_seq += 1
        offer = {
            "type": "offer",
            "offer_id": f"{self.buyer_id}-O{self.offer_seq}",
            "round": self.round,
            "lines": [
                {"sku": p.sku, "qty": q, "unit_price": self.unit[p.sku]} for p, q in self.lines
            ],
            "total": self.ask_total(),
            "floor_total": self.floor_total(),
            "note": self._note(),
            "claims": self._claims(),
        }
        if self.dropped:
            offer["unavailable"] = list(self.dropped)
        self.last_offer = offer
        return offer

    # ------------------------------------------------------------- protocol

    def start(self) -> dict:
        return self._emit_offer()

    def _counter_totals(self, msg: dict) -> tuple[int, int, str | None]:
        """Return (buyer_total, buyer_floor_total, error)."""
        raw = msg.get("lines")
        if not isinstance(raw, list) or len(raw) != len(self.lines):
            return 0, 0, "counter must price exactly the offered lines"
        by_sku = {p.sku: (p, q) for p, q in self.lines}
        total = floor_total = 0
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, dict):
                return 0, 0, "counter lines must be objects"
            sku = str(item.get("sku") or "")
            if sku in seen:
                return 0, 0, f"duplicate sku in counter: {sku!r}"
            seen.add(sku)
            if sku not in by_sku:
                return 0, 0, f"counter introduced sku {sku!r} that was never offered"
            product, agreed_qty = by_sku[sku]
            try:
                qty = int(item.get("qty", agreed_qty))
                unit = int(item.get("unit_price"))
            except (TypeError, ValueError):
                return 0, 0, "counter qty and unit_price must be integers"
            if qty != agreed_qty:
                return 0, 0, f"quantity for {sku} is fixed at {agreed_qty}"
            if unit <= 0:
                return 0, 0, f"unit_price must be positive for {sku}"
            total += unit * qty
            floor_total += self.policy.floor_unit(product) * qty
        if seen != set(by_sku):
            return 0, 0, "counter must price every offered line"
        return total, floor_total, None

    def _settle(self, lines: list[dict], total: int, offer_id: str, why: str) -> dict:
        self.closed = "accepted"
        self.final = {
            "type": "accept",
            "deal": True,
            "offer_id": offer_id,
            "lines": lines,
            "total": total,
            "basis": why,
        }
        return self.final

    def _walk(self, reason: str, buyer_total: int = 0) -> dict:
        self.closed = "walked_away"
        self.final = {
            "type": "walk_away",
            "deal": False,
            "reason": reason,
            "best_buyer_total": buyer_total,
            "floor_total": self.floor_total(),
        }
        return self.final

    def handle(self, msg: dict) -> dict:
        if self.closed:
            return {"type": "error", "error": "negotiation_closed", "state": self.closed}

        kind = msg.get("type")
        if kind == "accept":
            if not self.last_offer:
                return {"type": "error", "error": "nothing_to_accept"}
            return self._settle(
                self.last_offer["lines"],
                self.last_offer["total"],
                self.last_offer["offer_id"],
                "buyer_accepted_offer",
            )
        if kind == "walk_away":
            return self._walk("buyer_walked_away")
        if kind != "counter":
            return {"type": "error", "error": f"unknown_message_type:{kind}"}

        buyer_total, _buyer_floor, err = self._counter_totals(msg)
        if err:
            return {"type": "error", "error": err}
        if buyer_total <= 0:
            return self._walk("non_positive_total")

        ask = self.ask_total()
        if buyer_total >= ask:
            return self._settle(msg["lines"], buyer_total, msg.get("offer_id", ""), "met_ask")

        if self.round >= self.policy.max_rounds:
            if buyer_total >= self.floor_total():
                return self._settle(
                    msg["lines"], buyer_total, msg.get("offer_id", ""), "last_round_at_or_above_floor"
                )
            return self._walk("below_floor_at_final_round", buyer_total)

        improved = buyer_total > self.best_buyer_total
        self.best_buyer_total = max(self.best_buyer_total, buyer_total)
        self.round += 1

        if improved:
            gap = ask - buyer_total
            step = min(self.policy.per_round_step * self.opening_total(), self.policy.gap_share * gap)
            ask -= step
            target = max(self.min_total(), money(ask))
            self._concede(max(0, self.ask_total() - target))
        return self._emit_offer()


class SellerAgent:
    """Thin wrapper the harness uses; one Negotiation per buyer."""

    def __init__(self, store: Store, policy: Policy):
        self.store = store
        self.policy = policy

    def open(self, inquiry: dict) -> Negotiation:
        return Negotiation.open(self.store, self.policy, inquiry)
