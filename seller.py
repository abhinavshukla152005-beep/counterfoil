"""Counterfoil's seller agent in the official Techfest PS2 message format.

The official starter kit loads a ``Seller(store, policy)`` class and drives it
with ``start(negotiation_id)`` / ``respond(message)``. This file implements
that interface on top of the same rules the rest of the repository measures:
prices come from the ledger, concessions are earned, the policy floor is
absolute, and buyer prose is never read.

    python evaluate.py --seller seller.py --log transcripts.jsonl

Nothing here reads ``message["text"]``. Text is only written.
"""
import math

FLOOR_TOLERANCE = 0  # every unit price stays at or above the policy floor


class Seller:
    # Tuned on the official bots, seeds 0-2, then checked on unseen seeds.
    round_step = 0.10       # share of the list-to-floor gap released per round, once the buyer improves
    accept_share = 0.82     # accept once a bid covers this share of the ask-to-floor gap
    accept_decay = 0.0      # accept_share falls by this much each round
    final_theta = 0.90      # final round: offer the floor if the bid is this close to it

    def __init__(self, store, policy):
        self.store, self.policy = store, policy

    # ------------------------------------------------------------------ policy

    def floor(self, sku):
        row = self.store[sku]
        margin = self.policy["min_margin"][row["category"]]
        value = max(row["cost"] / (1 - margin), row["price"] * (1 - self.policy["max_discount"]))
        return math.ceil(value) + FLOOR_TOLERANCE

    # ------------------------------------------------------------------ state

    def start(self, negotiation_id):
        self.lines = []          # [{"sku", "qty"}] in the order first offered
        self.ask = {}            # sku -> our current unit price
        self.floors = {}         # sku -> policy floor per unit
        self.floor_total = 0
        self._best_bid = 0
        self._last_parsed = 0
        self._round = 1
        self._closed = False

    # ------------------------------------------------------------------ turns

    def respond(self, message):
        if self._closed:
            return {"type": "message", "text": ""}
        if not self.lines:
            return self._open(message)
        return self._turn(message)

    def _open(self, message):
        wanted = {}
        for item in message.get("items") or []:
            if not isinstance(item, dict):
                continue
            sku, qty = item.get("sku"), item.get("qty")
            if sku not in self.store or not isinstance(qty, int) or isinstance(qty, bool):
                continue
            take = min(qty, self.store[sku]["stock"])
            if take >= 1:
                wanted[sku] = take
        if not wanted:
            self._closed = True
            return {"type": "walk_away", "text": "We cannot supply that basket."}

        self.lines = [{"sku": sku, "qty": qty} for sku, qty in wanted.items()]
        self.floors = {sku: self.floor(sku) for sku in wanted}
        self.ask = {sku: self.store[sku]["price"] for sku in wanted}
        self.floor_total = sum(self.floors[line["sku"]] * line["qty"] for line in self.lines)
        self.list_total = sum(self.store[line["sku"]]["price"] * line["qty"] for line in self.lines)
        return self._offer()

    def _turn(self, message):
        round_no = message.get("round")
        round_no = round_no if isinstance(round_no, int) else 1
        self._round = round_no
        max_rounds = self.policy.get("max_rounds", 10)
        bid, extra = self._parse(message)
        bid_total = self._total(bid) if bid else 0
        if bid:
            self._last_parsed = bid_total

        if round_no >= max_rounds:
            self._closed = True
            if bid is not None and not extra and self._acceptable(bid):
                return {"type": "accept", "text": "Deal."}
            signal = bid_total if bid else self._last_parsed
            if signal >= int(self.final_theta * self.floor_total):
                self._drop_to(self.floor_total)
                return self._offer()
            return {"type": "walk_away", "text": "That basket is outside what we can do. Thank you."}

        if bid is not None and not extra and self._acceptable(bid):
            gap = max(0, self._ask_total() - self.floor_total)
            share = max(0.0, self.accept_share - self.accept_decay * (round_no - 1))
            reserve = self.floor_total + int(round(share * gap))
            if bid_total >= reserve:
                self._closed = True
                return {"type": "accept", "text": "Deal."}

        if bid_total > self._best_bid:
            self._best_bid = bid_total
            self._concede(bid_total)
        return self._offer()

    # ------------------------------------------------------------------ helpers

    def _parse(self, message):
        """(our lines priced by the buyer, whether the buyer added anything else).

        Extra lines are tolerated for signalling - a tricked counter still says
        how far the buyer has moved - but they can never be accepted, because a
        deal is the buyer's whole basket.
        """
        if message.get("type") not in ("request", "counter"):
            return None, False
        items = message.get("items")
        if not isinstance(items, list) or not items:
            return None, False
        wanted = {line["sku"]: line["qty"] for line in self.lines}
        prices = {}
        extra = False
        for item in items:
            if not isinstance(item, dict):
                extra = True
                continue
            sku, qty, price = item.get("sku"), item.get("qty"), item.get("unit_price")
            if sku not in wanted or qty != wanted[sku] or not isinstance(price, (int, float)) \
                    or isinstance(price, bool):
                extra = True
                continue
            prices[sku] = price
        if len(prices) != len(wanted):
            return None, extra
        out = [{"sku": line["sku"], "qty": line["qty"], "unit_price": prices[line["sku"]]}
               for line in self.lines]
        return out, extra or len(items) != len(out)

    def _acceptable(self, bid):
        return all(self.floors[line["sku"]] <= line["unit_price"] <= self.store[line["sku"]]["price"]
                   for line in bid)

    def _total(self, items):
        return sum(line["qty"] * line["unit_price"] for line in items)

    def _ask_total(self):
        return sum(self.ask[line["sku"]] * line["qty"] for line in self.lines)

    def _concede(self, bid_total):
        """Release a fixed share of the list-to-floor gap per round the buyer improves."""
        gap = self.list_total - self.floor_total
        hold = max(0.0, 1.0 - self.round_step * self._round)
        self._drop_to(self.floor_total + int(round(hold * gap)))

    def _drop_to(self, target_total):
        """Lower unit prices, largest headroom first, until the basket total is at target."""
        target = max(self.floor_total, target_total)
        remaining = self._ask_total() - target
        if remaining <= 0:
            return
        while remaining > 0:
            move = None
            for line in self.lines:
                sku = line["sku"]
                head = self.ask[sku] - self.floors[sku]
                if head > 0 and (move is None or head > move[0]):
                    move = (head, sku, line["qty"])
            if move is None:
                return
            _, sku, qty = move
            take = min(self.ask[sku] - self.floors[sku], max(1, remaining // qty))
            self.ask[sku] -= take
            remaining -= take * qty

    def _offer(self):
        items = [{"sku": line["sku"], "qty": line["qty"], "unit_price": self.ask[line["sku"]]}
                 for line in self.lines]
        total = self._total(items)
        names = " and ".join(f"{line['qty']} x {self.store[line['sku']]['name']}" for line in self.lines)
        return {"type": "offer", "items": items, "text": f"{names} for \u20b9{total:,}. No fees on top."}
