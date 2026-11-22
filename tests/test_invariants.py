"""Invariants the seller must never break. Run: python tests/test_invariants.py

No pytest needed - plain asserts so the pack runs on a bare Python install.
"""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.bots import (  # noqa: E402
    Cooperative,
    Fuzzer,
    HardBargainer,
    Lowballer,
    Manipulator,
    Stonewall,
    counter,
)
from src.catalog import Policy, Store  # noqa: E402
from src.rezolve import (  # noqa: E402
    LocalVerifier,
    RezolveLabsVerifier,
    get_verifier,
    screening_gate,
)
from src.seller import InquiryError, Negotiation, SellerAgent  # noqa: E402

STORE = Store.load(ROOT / "store.csv")
POLICY = Policy.load(ROOT / "policy.json")
PASSED: list[str] = []


def check(name: str, fn) -> None:
    fn()
    PASSED.append(name)


def drive(neg: Negotiation, bot) -> dict:
    current = neg.start()
    steps = 0
    while current.get("type") == "offer" and steps < 60:
        response = neg.handle(bot.reply(current))
        steps += 1
        if response.get("type") == "error":
            continue
        current = response
    return current


def test_floor_never_crossed() -> None:
    rng = random.Random(2026)
    stocked = [p for p in STORE.all() if p.stock > 0]
    for _ in range(300):
        picks = rng.sample(stocked, rng.randint(1, 4))
        inquiry = {"buyer_id": "fuzz", "lines": [{"sku": p.sku, "qty": rng.randint(1, 3)} for p in picks]}
        neg = Negotiation.open(STORE, POLICY, inquiry)
        offer = neg.start()
        for _ in range(12):
            if offer.get("type") != "offer":
                break
            for line in offer["lines"]:
                product = STORE.get(line["sku"])
                assert line["unit_price"] >= POLICY.floor_unit(product), (
                    f"{line['sku']} {line['unit_price']} < floor {POLICY.floor_unit(product)}"
                )
                assert line["qty"] <= product.stock
            target = max(1, offer["total"] * 0.99)
            reply = neg.handle(counter(offer, int(target)))
            if reply.get("type") != "error":
                offer = reply


def test_text_cannot_move_numbers() -> None:
    """Same arithmetic, adversarial prose: identical price path."""
    for seed in range(1, 41):
        paths = []
        for bot_cls in (HardBargainer, Manipulator):
            bot = bot_cls(STORE, seed)
            neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
            current = neg.start()
            path = [current["total"]]
            steps = 0
            while current.get("type") == "offer" and steps < 40:
                current = neg.handle(bot.reply(current))
                steps += 1
                if current.get("type") == "offer":
                    path.append(current["total"])
            paths.append((path, (neg.final or {}).get("total")))
        assert paths[0] == paths[1], f"seed {seed} diverged: {paths}"


def test_deterministic() -> None:
    for seed in (5, 17, 23):
        runs = []
        for _ in range(3):
            bot = HardBargainer(STORE, seed)
            neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
            drive(neg, bot)
            runs.append(json.dumps(neg.final, sort_keys=True))
        assert len(set(runs)) == 1, f"seed {seed} not deterministic: {runs}"


def test_fairness_same_need_same_offer() -> None:
    """Two buyers with the same basket get the same first quote, regardless of id."""
    basket = [{"sku": p.sku, "qty": 2} for p in sorted(STORE.all(), key=lambda x: x.sku)[:3]]
    totals = {
        Negotiation.open(STORE, POLICY, {"buyer_id": bid, "lines": basket}).start()["total"]
        for bid in ("alice", "bob", "acme-corp", "x")
    }
    assert len(totals) == 1, totals


def test_inventory_is_respected() -> None:
    dead = [p for p in STORE.all() if p.stock == 0]
    assert dead, "store should contain at least one out-of-stock sku for the test to mean anything"
    live = [p for p in STORE.all() if p.stock > 0][0]
    inquiry = {
        "buyer_id": "stock",
        "lines": [
            {"sku": dead[0].sku, "qty": 1},
            {"sku": "SKU-0000-NOPE", "qty": 1},
            {"sku": live.sku, "qty": 999},
        ],
    }
    offer = Negotiation.open(STORE, POLICY, inquiry).start()
    reasons = {d["reason"] for d in offer["unavailable"]}
    assert reasons == {"out_of_stock", "unknown_sku", "qty_clamped"}, reasons
    line = next(l for l in offer["lines"] if l["sku"] == live.sku)
    assert line["qty"] == live.stock


def test_rejects_impossible_inquiry() -> None:
    for bad in (
        {"buyer_id": "x", "lines": []},
        {"buyer_id": "x", "lines": [{"sku": "SKU-0001", "qty": 0}]},
        {"buyer_id": "x", "lines": [{"sku": "SKU-0001", "qty": -2}]},
        {"buyer_id": "x", "lines": [{"sku": "SKU-0001", "qty": 1}, {"sku": "SKU-0001", "qty": 1}]},
    ):
        try:
            Negotiation.open(STORE, POLICY, bad)
        except InquiryError:
            continue
        raise AssertionError(f"accepted an impossible inquiry: {bad}")


def test_claims_all_supported() -> None:
    verifier = LocalVerifier(STORE, POLICY)
    for bot_cls in (Cooperative, HardBargainer, Stonewall):
        bot = bot_cls(STORE, 9)
        neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
        current = neg.start()
        steps = 0
        while current.get("type") == "offer" and steps < 30:
            verdicts = verifier.verify(current["claims"], current)
            assert screening_gate(verdicts) is None, screening_gate(verdicts)
            assert len(verdicts) == len(current["claims"])
            current = neg.handle(bot.reply(current))
            steps += 1


def test_malformed_counters_are_typed_errors() -> None:
    bot = Cooperative(STORE, 3)
    neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
    offer = neg.start()
    bad = [
        {"type": "counter", "lines": []},
        {"type": "counter", "lines": [{"sku": "SKU-9999", "qty": 1, "unit_price": 10}]},
        {"type": "counter", "lines": [dict(l, unit_price="x") for l in offer["lines"]]},
        {"type": "counter", "lines": [dict(l, qty=l["qty"] + 5) for l in offer["lines"]]},
        {"type": "counter", "lines": [dict(l, unit_price=0) for l in offer["lines"]]},
        {"type": "teleport"},
    ]
    for msg in bad:
        reply = neg.handle(msg)
        assert reply["type"] == "error", (msg, reply)
        assert neg.closed is None
    assert neg.handle({"type": "accept", "offer_id": offer["offer_id"]})["deal"] is True


def test_below_floor_walks_away() -> None:
    bot = Lowballer(STORE, 4)
    neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
    final = drive(neg, bot)
    assert final["type"] == "walk_away", final
    assert final["reason"] == "below_floor_at_final_round"


def test_cannot_reopen_closed_negotiation() -> None:
    bot = Cooperative(STORE, 6)
    neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
    offer = neg.start()
    neg.handle({"type": "accept", "offer_id": offer["offer_id"]})
    again = neg.handle({"type": "counter", "lines": offer["lines"]})
    assert again["type"] == "error" and again["error"] == "negotiation_closed"


def test_fuzzer_never_crashes_seller() -> None:
    for seed in range(1, 26):
        bot = Fuzzer(STORE, seed)
        neg = SellerAgent(STORE, POLICY).open(bot.inquiry)
        current = neg.start()
        assert current["type"] == "offer"
        steps = 0
        while current.get("type") == "offer" and steps < 40:
            response = neg.handle(bot.reply(current))
            steps += 1
            if response.get("type") == "error":
                continue
            current = response
        assert (neg.final or {}).get("deal") is True, (seed, current)


def test_store_integrity() -> None:
    products = STORE.all()
    assert len(products) == 96, len(products)
    assert len({p.sku for p in products}) == 96
    for p in products:
        assert p.cost < p.list_price, p
        assert p.stock >= 0
        assert POLICY.floor_unit(p) <= p.list_price, (p.sku, POLICY.floor_unit(p), p.list_price)
        assert POLICY.floor_unit(p) > p.cost, (p.sku, "floor must stay above cost")


def test_verifier_catches_a_lie() -> None:
    """The gate has to fire, otherwise 'zero contradictions' means nothing."""
    verifier = LocalVerifier(STORE, POLICY)
    offer = Negotiation.open(STORE, POLICY, Cooperative(STORE, 2).inquiry).start()
    clean = verifier.verify(offer["claims"], offer)
    assert screening_gate(clean) is None

    tampered = [dict(c) for c in offer["claims"]]
    priced = next(c for c in tampered if c["field"] == "list_price")
    priced["value"] = priced["value"] - 1
    stock = next(c for c in tampered if c["field"] == "stock")
    stock["value"] = stock["value"] + 40

    verdicts = verifier.verify(tampered, offer)
    assert sum(1 for v in verdicts if v["verdict"] == "contradict") == 2, verdicts
    problem = screening_gate(verdicts)
    assert problem and "store says" in problem, problem


def test_unknown_claim_fields_are_not_silently_supported() -> None:
    verifier = LocalVerifier(STORE, POLICY)
    offer = Negotiation.open(STORE, POLICY, Cooperative(STORE, 2).inquiry).start()
    verdicts = verifier.verify(
        [{"sku": "SKU-0000", "field": "list_price", "value": 1}, {"field": "rumour", "value": 1}],
        offer,
    )
    assert [v["verdict"] for v in verdicts] == ["unknown", "unknown"], verdicts


def test_hosted_verifier_degrades_instead_of_guessing() -> None:
    """A dead endpoint must fall back to the reference verifier, not to silence."""
    local = LocalVerifier(STORE, POLICY)
    dead = RezolveLabsVerifier("http://127.0.0.1:9", "not-a-real-key", local)
    offer = Negotiation.open(STORE, POLICY, Cooperative(STORE, 2).inquiry).start()
    verdicts = dead.verify(offer["claims"], offer)
    assert dead.degraded is True
    assert verdicts == local.verify(offer["claims"], offer)


def test_verifier_selection_follows_environment() -> None:
    import os

    saved = {k: os.environ.pop(k, None) for k in ("REZOLVE_BASE_URL", "REZOLVE_API_KEY")}
    try:
        assert isinstance(get_verifier(STORE, POLICY), LocalVerifier)
        os.environ["REZOLVE_BASE_URL"] = "https://example.invalid"
        os.environ["REZOLVE_API_KEY"] = "k"
        assert isinstance(get_verifier(STORE, POLICY), RezolveLabsVerifier)
    finally:
        for key in ("REZOLVE_BASE_URL", "REZOLVE_API_KEY"):
            os.environ.pop(key, None)
            if saved[key] is not None:
                os.environ[key] = saved[key]


TESTS = [
    ("store integrity", test_store_integrity),
    ("floor never crossed", test_floor_never_crossed),
    ("text cannot move numbers", test_text_cannot_move_numbers),
    ("deterministic", test_deterministic),
    ("fairness: same need, same offer", test_fairness_same_need_same_offer),
    ("inventory respected", test_inventory_is_respected),
    ("impossible inquiry rejected", test_rejects_impossible_inquiry),
    ("every claim supported", test_claims_all_supported),
    ("verifier catches a lie", test_verifier_catches_a_lie),
    ("unknown claim fields are unknown", test_unknown_claim_fields_are_not_silently_supported),
    ("hosted verifier degrades safely", test_hosted_verifier_degrades_instead_of_guessing),
    ("verifier selection follows environment", test_verifier_selection_follows_environment),
    ("malformed counters are typed errors", test_malformed_counters_are_typed_errors),
    ("below-floor buyer walks away", test_below_floor_walks_away),
    ("closed negotiation stays closed", test_cannot_reopen_closed_negotiation),
    ("fuzzer never crashes the seller", test_fuzzer_never_crashes_seller),
]


def main() -> int:
    failures = 0
    for name, fn in TESTS:
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"FAIL  {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok    {name}")
    print(f"\n{len(TESTS) - failures}/{len(TESTS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
