"""Round-1 harness: run every bot policy against the seller and log it all.

Writes ``outputs/transcripts.jsonl`` (one JSON object per negotiation, with the
full message log) and ``outputs/summary.json``. The evaluator reads only those
two files, so the numbers in RESULTS.md are reproducible from the artefacts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.bots import ALL_BOTS  # noqa: E402
from src.catalog import Policy, Store  # noqa: E402
from src.rezolve import get_verifier, screening_gate  # noqa: E402
from src.seller import InquiryError, SellerAgent  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MAX_STEPS = 80
SEEDS = range(1, 16)


def _cost_of(store: Store, lines: list[dict]) -> int:
    total = 0
    for line in lines:
        product = store.get(line["sku"])
        if product is not None:
            total += product.cost * int(line["qty"])
    return total


def _list_of(store: Store, lines: list[dict]) -> int:
    total = 0
    for line in lines:
        product = store.get(line["sku"])
        if product is not None:
            total += product.list_price * int(line["qty"])
    return total


def run_one(store: Store, policy: Policy, bot_cls, seed: int, verifier) -> dict:
    bot = bot_cls(store, seed * 1000 + 7)
    run_id = f"{bot.name}/s{seed:02d}"
    seller = SellerAgent(store, policy)
    log: list[dict] = []
    verdicts: list[dict] = []
    withheld: list[str] = []

    record = {
        "run_id": run_id,
        "bot": bot.name,
        "seed": seed,
        "deal": False,
        "rounds": 0,
        "steps": 0,
        "agreed_total": 0,
        "opening_total": 0,
        "floor_total": 0,
        "list_total": 0,
        "cost_total": 0,
        "units": 0,
        "errors": [],
        "withheld": withheld,
        "claims_checked": 0,
        "claims_supported": 0,
        "claims_contradicted": 0,
        "inquiry": bot.inquiry,
    }

    try:
        neg = seller.open(bot.inquiry)
    except InquiryError as exc:
        record["errors"].append(f"inquiry_rejected: {exc}")
        record["transcript"] = log
        return record

    def release(offer: dict) -> dict:
        result = verifier.verify(offer.get("claims", []), offer)
        verdicts.extend(result)
        problem = screening_gate(result)
        if problem:
            withheld.append(problem)
            return {"type": "error", "error": "offer_withheld_by_verifier", "detail": problem}
        return {**offer, "verification": result}

    current = release(neg.start())
    record["opening_total"] = neg.ask_total()
    record["floor_total"] = neg.floor_total()
    record["list_total"] = _list_of(store, [{"sku": p.sku, "qty": q} for p, q in neg.lines])
    record["cost_total"] = _cost_of(store, [{"sku": p.sku, "qty": q} for p, q in neg.lines])
    record["units"] = sum(q for _, q in neg.lines)
    log.append({"seq": len(log), "role": "seller", "msg": current})

    steps = 0
    while current.get("type") == "offer" and steps < MAX_STEPS:
        reply = bot.reply(current)
        log.append({"seq": len(log), "role": "buyer", "msg": reply})
        response = neg.handle(reply)
        log.append({"seq": len(log), "role": "seller", "msg": response})
        steps += 1
        if response.get("type") == "error":
            record["errors"].append(str(response.get("error")))
            continue
        current = response
        if current.get("type") == "offer":
            current = release(current)
            log.append({"seq": len(log), "role": "verifier", "msg": current.get("verification", [])})

    record["steps"] = steps
    record["rounds"] = neg.round
    if neg.final is None:
        neg._walk("step_budget_exhausted")
    final = neg.final or {}
    record["deal"] = bool(final.get("deal"))
    record["agreed_total"] = int(final.get("total") or 0)
    record["final_lines"] = final.get("lines") or []
    record["claims_checked"] = len(verdicts)
    record["claims_supported"] = sum(1 for v in verdicts if v.get("verdict") == "support")
    record["claims_contradicted"] = sum(1 for v in verdicts if v.get("verdict") == "contradict")
    record["transcript"] = log
    return record


def main() -> int:
    store = Store.load(ROOT / "store.csv")
    policy = Policy.load(ROOT / "policy.json")
    verifier = get_verifier(store, policy)
    out_dir = ROOT / "outputs"
    out_dir.mkdir(exist_ok=True)

    records = []
    for bot_cls in ALL_BOTS:
        for seed in SEEDS:
            records.append(run_one(store, policy, bot_cls, seed, verifier))

    with (out_dir / "transcripts.jsonl").open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, sort_keys=True) + "\n")

    summary = {
        "verifier": verifier.name,
        "degraded": bool(getattr(verifier, "degraded", False)),
        "negotiations": len(records),
        "bots": {},
    }
    for record in records:
        bucket = summary["bots"].setdefault(record["bot"], {"runs": 0, "deals": 0, "agreed_total": 0})
        bucket["runs"] += 1
        bucket["deals"] += int(record["deal"])
        bucket["agreed_total"] += record["agreed_total"]
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"{len(records)} negotiations -> {out_dir / 'transcripts.jsonl'}")
    for name, b in summary["bots"].items():
        rate = b["deals"] / b["runs"]
        print(f"  {name:15s} deals {b['deals']:2d}/{b['runs']:2d} ({rate:.0%})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
