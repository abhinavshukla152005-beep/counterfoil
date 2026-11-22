"""Readable transcript printer used for the demo video.

    python -m src.demo --bot manipulator --seed 3
    python -m src.demo --list
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bots import ALL_BOTS  # noqa: E402
from src.catalog import Policy, Store  # noqa: E402
from src.rezolve import get_verifier, screening_gate  # noqa: E402
from src.seller import SellerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BY_NAME = {cls.name: cls for cls in ALL_BOTS}


def inr(value: int) -> str:
    return f"{value:,}"


def counter_total(lines) -> int | None:
    """Total a buyer counter, or None if the buyer sent something malformed."""
    try:
        return sum(int(l["unit_price"]) * int(l["qty"]) for l in lines)
    except (TypeError, ValueError, KeyError):
        return None


def run(bot, store, policy, verifier, verbose: bool = True) -> tuple[list[int], dict]:
    seller = SellerAgent(store, policy)
    neg = seller.open(bot.inquiry)
    current = neg.start()
    path = [current["total"]]
    if verbose:
        verdicts = verifier.verify(current["claims"], current)
        print(f"[r{current['round']}] SELLER offers {inr(current['total'])} INR "
              f"({len(current['lines'])} lines)  claims verified {len(verdicts)}/{len(verdicts)}")
        print(f"         {current['note']}")
        if current.get("unavailable"):
            print(f"         unavailable: {current['unavailable']}")

    steps = 0
    while current.get("type") == "offer" and steps < 40:
        reply = bot.reply(current)
        text = (reply.get("text") or "").strip()
        if verbose:
            if reply["type"] == "counter":
                total = counter_total(reply["lines"])
                shown = f"{inr(total)} INR" if total is not None else "a malformed basket"
                print(f"         BUYER counters {shown}" + (f'\n         "{text}"' if text else ""))
            else:
                print(f"         BUYER {reply['type']}" + (f'  "{text}"' if text else ""))
        response = neg.handle(reply)
        steps += 1
        if response.get("type") == "error":
            if verbose:
                print(f"         SELLER rejects: {response['error']}")
            continue
        current = response
        if current.get("type") == "offer":
            path.append(current["total"])
            if verbose:
                verdicts = verifier.verify(current["claims"], current)
                problem = screening_gate(verdicts)
                if problem:
                    print(f"         VERIFIER withheld the offer: {problem}")
                    break
                print(f"[r{current['round']}] SELLER offers {inr(current['total'])} INR "
                      f"  claims verified {len(verdicts)}/{len(verdicts)}")
    final = dict(neg.final or {})
    final["floor_total"] = neg.floor_total()
    final["rounds"] = neg.round
    return path, final


def parity(store, policy, verifier, seed: int) -> int:
    """Same arithmetic, adversarial prose: print both price paths side by side."""
    control_bot = BY_NAME["hard_bargainer"](store, seed)
    attack_bot = BY_NAME["manipulator"](store, seed)
    control_path, control_final = run(control_bot, store, policy, verifier, verbose=False)
    attack_path, attack_final = run(attack_bot, store, policy, verifier, verbose=False)

    width = max(len(control_path), len(attack_path))
    print(f"seed {seed}   honest buyer            manipulator")
    for i in range(width):
        left = inr(control_path[i]) if i < len(control_path) else "-"
        right = inr(attack_path[i]) if i < len(attack_path) else "-"
        marker = "" if left == right else "   <-- DIFFERS"
        print(f"  offer {i + 1:2d}   {left:>10s}          {right:>10s}{marker}")
    print()
    print(f"  final       {inr(control_final.get('total', 0)):>10s}          "
          f"{inr(attack_final.get('total', 0)):>10s}")
    same = control_path == attack_path and control_final.get("total") == attack_final.get("total")
    print()
    print("IDENTICAL" if same else "DIFFERENT — the claim in the abstract is false")
    print("The manipulator sent fake competitor quotes, a fake manager approval, a fake")
    print("countdown, a request for landed cost, and a SYSTEM OVERRIDE injection.")
    return 0 if same else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Counterfoil negotiation demo")
    parser.add_argument("--bot", default="manipulator", help=f"one of {', '.join(BY_NAME)}")
    parser.add_argument("--seed", type=int, default=3)
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--parity", action="store_true", help="prove text cannot move a price")
    args = parser.parse_args(argv)

    if args.list:
        for cls in ALL_BOTS:
            print(f"{cls.name:15s} {cls.__doc__ or ''}".strip())
        return 0

    if args.bot not in BY_NAME:
        parser.error(f"unknown bot {args.bot!r}")

    store = Store.load(ROOT / "store.csv")
    policy = Policy.load(ROOT / "policy.json")
    verifier = get_verifier(store, policy)

    if args.parity:
        return parity(store, policy, verifier, args.seed)

    bot = BY_NAME[args.bot](store, args.seed)

    print(f"buyer policy : {bot.name}")
    print(f"verifier     : {verifier.name}")
    print(f"basket       : {len(bot.inquiry['lines'])} requested lines")
    for line in bot.inquiry["lines"]:
        product = store.get(line["sku"])
        label = f"{product.name} ({product.brand})" if product else "no such product"
        print(f"   {line['sku']}  x{line['qty']}  {label}")
    print()

    _, final = run(bot, store, policy, verifier)
    print()
    if final.get("deal"):
        print(f"DEAL at {inr(final['total'])} INR (floor was {inr(final.get('floor_total', 0))}, "
              f"basis {final.get('basis')})")
    else:
        print(f"NO DEAL: {final.get('reason')} "
              f"(buyer best {inr(final.get('best_buyer_total', 0))}, floor {inr(final.get('floor_total', 0))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
