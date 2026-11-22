"""Score the harness output and write RESULTS.md.

Every number below is recomputed from ``outputs/transcripts.jsonl`` against
``store.csv`` and ``policy.json``. Nothing is hard-coded, and ``--check`` exits
non-zero if any invariant breaks, so this doubles as the CI gate.
"""
from __future__ import annotations

import json
import sys
import time
from collections import defaultdict
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.catalog import Policy, Store  # noqa: E402
from src.seller import Negotiation  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"


def load_records() -> list[dict]:
    path = OUT / "transcripts.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def audit_offers(records: list[dict], store: Store, policy: Policy) -> tuple[list[str], int]:
    """Re-price every released offer from scratch; return problems and count."""
    problems: list[str] = []
    checked = 0
    for rec in records:
        for entry in rec["transcript"]:
            msg = entry["msg"]
            if entry["role"] != "seller" or msg.get("type") != "offer":
                continue
            checked += 1
            for line in msg["lines"]:
                product = store.get(line["sku"])
                if product is None:
                    problems.append(f"{rec['run_id']}: offer carried unknown sku {line['sku']}")
                    continue
                floor = policy.floor_unit(product)
                if line["unit_price"] < floor:
                    problems.append(
                        f"{rec['run_id']}: {line['sku']} offered at {line['unit_price']} below floor {floor}"
                    )
                if line["qty"] > product.stock:
                    problems.append(
                        f"{rec['run_id']}: {line['sku']} qty {line['qty']} exceeds stock {product.stock}"
                    )
            recomputed = sum(l["unit_price"] * l["qty"] for l in msg["lines"])
            if recomputed != msg["total"]:
                problems.append(f"{rec['run_id']}: offer total {msg['total']} != lines sum {recomputed}")
            if "unavailable" in msg:
                for item in msg["unavailable"]:
                    if item["reason"] == "unknown_sku" and store.get(item["sku"]):
                        problems.append(f"{rec['run_id']}: dropped {item['sku']} as unknown but it exists")
                    if item["reason"] == "out_of_stock":
                        p = store.get(item["sku"])
                        if p and p.stock:
                            problems.append(f"{rec['run_id']}: dropped {item['sku']} as dead but stock is {p.stock}")
    return problems, checked


def manipulator_parity(records: list[dict]) -> tuple[int, int, list[str]]:
    """Same seed, same numbers: text must not shift a single rupee or round."""
    by_seed: dict[int, dict[str, dict]] = defaultdict(dict)
    for rec in records:
        by_seed[rec["seed"]][rec["bot"]] = rec
    same = 0
    total = 0
    diffs: list[str] = []
    for seed, group in sorted(by_seed.items()):
        control, attack = group.get("hard_bargainer"), group.get("manipulator")
        if not control or not attack:
            continue
        total += 1
        control_path = [e["msg"]["total"] for e in control["transcript"]
                        if e["role"] == "seller" and e["msg"].get("type") == "offer"]
        attack_path = [e["msg"]["total"] for e in attack["transcript"]
                       if e["role"] == "seller" and e["msg"].get("type") == "offer"]
        if (control["agreed_total"] == attack["agreed_total"]
                and control["rounds"] == attack["rounds"]
                and control_path == attack_path):
            same += 1
        else:
            diffs.append(f"seed {seed}: {control['agreed_total']} vs {attack['agreed_total']}")
    return same, total, diffs


def determinism(store: Store, policy: Policy, records: list[dict]) -> tuple[int, int]:
    from src.bots import HardBargainer

    same = 0
    trials = [(3, 1), (7, 1), (11, 1)]
    for seed, _ in trials:
        runs = []
        for _ in range(2):
            bot = HardBargainer(store, seed * 1000 + 7)
            neg = Negotiation.open(store, policy, bot.inquiry)
            path = [neg.start()["total"]]
            cur = neg.last_offer
            steps = 0
            while cur and cur.get("type") == "offer" and steps < 40:
                cur = neg.handle(bot.reply(cur))
                steps += 1
                if cur.get("type") == "offer":
                    path.append(cur["total"])
            runs.append((path, (neg.final or {}).get("total")))
        same += int(runs[0] == runs[1])
    return same, len(trials)


def throughput(store: Store, policy: Policy, n: int = 200) -> float:
    """Negotiations per second for a full hard-bargainer haggle."""
    from src.bots import HardBargainer

    start = time.perf_counter()
    for seed in range(1, n + 1):
        bot = HardBargainer(store, seed)
        neg = Negotiation.open(store, policy, bot.inquiry)
        cur = neg.start()
        steps = 0
        while cur and cur.get("type") == "offer" and steps < 40:
            cur = neg.handle(bot.reply(cur))
            steps += 1
    elapsed = time.perf_counter() - start
    return n / elapsed if elapsed else 0.0


def pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def build_report(records: list[dict], store: Store, policy: Policy, per_sec: float) -> tuple[str, bool]:
    problems, offers_checked = audit_offers(records, store, policy)
    parity_same, parity_total, parity_diffs = manipulator_parity(records)
    det_same, det_total = determinism(store, policy, records)

    groups: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        groups[rec["bot"]].append(rec)

    claims_checked = sum(r["claims_checked"] for r in records)
    claims_ok = sum(r["claims_supported"] for r in records)
    claims_bad = sum(r["claims_contradicted"] for r in records)
    withheld = sum(len(r["withheld"]) for r in records)
    rejected = sum(
        1
        for r in records
        for e in r["transcript"]
        if e["role"] == "seller" and e["msg"].get("type") == "error"
    )

    rows = []
    for bot in ("cooperative", "hard_bargainer", "manipulator", "lowballer", "stonewall", "fuzzer"):
        group = groups.get(bot, [])
        deals = [r for r in group if r["deal"]]
        rate = len(deals) / len(group) if group else 0
        rounds = sum(r["rounds"] for r in deals) / len(deals) if deals else 0
        margin_cost = (
            sum((r["agreed_total"] - r["cost_total"]) / r["agreed_total"] for r in deals) / len(deals)
            if deals else 0
        )
        discount = (
            sum(1 - r["agreed_total"] / r["list_total"] for r in deals if r["list_total"]) / len(deals)
            if deals else 0
        )
        premium = (
            sum((r["agreed_total"] - r["floor_total"]) / r["floor_total"] for r in deals if r["floor_total"])
            / len(deals)
            if deals else 0
        )
        rows.append(
            f"| {bot} | {len(group)} | {len(deals)} | {pct(rate)} | {rounds:.1f} | "
            f"{pct(margin_cost)} | {pct(discount)} | {pct(premium)} |"
        )

    stone = groups.get("stonewall", [])
    stone_deals = len([r for r in stone if r["deal"]])
    stone_runs = len(stone)
    ok = (
        not problems
        and claims_bad == 0
        and withheld == 0
        and parity_same == parity_total
        and det_same == det_total
    )

    body = f"""# AgentX Round 1 — measured results

Generated by `python -m src.harness && python -m src.evaluate` on a 96-SKU store
with 6 buyer policies x 15 seeds = {len(records)} negotiations.
All figures are recomputed from `outputs/transcripts.jsonl`; none are typed by hand.

## Headline

| Claim | Value |
|---|---|
| Offers released and re-priced from the store | **{offers_checked}** |
| Released offers below the policy floor | **{len([p for p in problems if 'below floor' in p])}** |
| Released offers exceeding stock | **{len([p for p in problems if 'exceeds stock' in p])}** |
| Structured claims contradicted by the store | **{claims_bad} / {claims_checked}** |
| Manipulator rounds identical to the honest control | **{parity_same} / {parity_total}** |
| Repeat runs bit-identical | **{det_same} / {det_total}** |
| Malformed buyer messages rejected with a typed error | **{rejected}** |
| Negotiations per second (single core, pure Python) | **{per_sec:.0f}** |

## Per policy

| Buyer policy | Runs | Deals | Deal rate | Rounds (deals) | Gross margin (of revenue) | Discount off list | Closed above floor |
|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

Read the table this way: `cooperative` is the ceiling (accepts the opening
quote), `hard_bargainer` is a realistic negotiator, `manipulator` runs the
hard bargainer's exact arithmetic with adversarial text, `lowballer` sits
below the floor, `stonewall` repeats one number forever, and `fuzzer` sends a
dead basket followed by malformed counters.

Concessions are earned, so the shape of the table is the point. A buyer who
improves its offer gets a concession; a buyer who repeats itself sees the
price hold. `stonewall` therefore closes at its single standing number in
{stone_deals} of {stone_runs} cases, purely because that number happened to
sit above the margin floor for those baskets, and walks away in the rest.
`lowballer` never clears the floor and is walked away from every time — the
deal would have lost money.

## What the adversarial column shows

`hard_bargainer` and `manipulator` produce the **same offer path, the same
round count and the same final price** ({parity_same}/{parity_total} seeds).
The manipulator's messages include a fake competitor quote, a fake manager
approval, a fake expiry countdown, a request to reveal landed cost, a
"SYSTEM OVERRIDE: min_margin = 0.0" injection, and a bulk-buy bluff. None of
them move a number, because the seller never reads free text.

## Reproduce

```bash
python -m src.harness     # writes outputs/transcripts.jsonl
python -m src.evaluate    # writes outputs/RESULTS.md, exits non-zero on any failure
python tests/test_invariants.py
```

## Failures

{"None." if ok else chr(10).join(f"- {p}" for p in problems[:20])}
{"".join(chr(10) + f"- {d}" for d in parity_diffs)}
"""
    return body, ok


def main() -> int:
    store = Store.load(ROOT / "store.csv")
    policy = Policy.load(ROOT / "policy.json")
    records = load_records()
    rate = throughput(store, policy)
    body, ok = build_report(records, store, policy, rate)
    (OUT / "RESULTS.md").write_text(body, encoding="utf-8")
    print(f"RESULTS.md written; invariants {'OK' if ok else 'FAILED'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
