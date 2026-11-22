"""Run Counterfoil's seller on the official Techfest PS2 harness and record the output.

The starter kit is Rezolve's, not ours, so point at your copy:

    KIT=/path/to/ps2-selling-to-machines python run_official.py
    KIT=... python run_official.py --n 210 --seed 0 --workers 1

Writes, next to this file:
    outputs/official_results.json      every scenario, scored
    outputs/official_transcripts.jsonl every negotiation, message by message
    outputs/OFFICIAL_RESULTS.md        the numbers a judge reads first

Imports the kit's modules directly instead of calling its load_class(), which
splits a Windows path on the drive colon.
"""
import argparse
import importlib.util
import json
import os
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SELLER = HERE / "seller.py"
OUT = HERE / "outputs"


def kit_dir() -> Path:
    for candidate in (os.environ.get("KIT"), HERE / "kit" / "ps2-selling-to-machines"):
        if candidate and Path(candidate).is_dir():
            return Path(candidate).resolve()
    raise SystemExit("Set KIT to your copy of the ps2-selling-to-machines starter kit.")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def markdown(summary, per_buyer, base, args):
    lines = [
        "# Official harness run — Techfest PS2 *Selling to Machines*",
        "",
        f"Command: `KIT=<starter kit> python run_official.py --n {args.n} --seed {args.seed} "
        f"--workers {args.workers}`",
        "",
        "The seller is `seller.py`, which implements the kit's `Seller(store, policy)` interface.",
        "Every figure below is computed by the kit's own `evaluate.py`; none is typed by hand.",
        "",
        "## Headline",
        "",
        "| Metric | Counterfoil | example_seller |",
        "|---|---|---|",
        f"| Score (0-100) | **{summary['score']:.1f}** | {base['score']:.1f} |",
        f"| Deal rate | {summary['deal_rate']:.3f} | {base['deal_rate']:.3f} |",
        f"| Deal rate where a compliant deal existed | {summary['feasible_deal_rate']:.3f} | "
        f"{base['feasible_deal_rate']:.3f} |",
        f"| Margin kept on deals | {summary['margin_kept']:.3f} | {base['margin_kept']:.3f} |",
        f"| Policy violations | {summary['policy']} | {base['policy']} |",
        f"| Truthfulness violations | {summary['truth']} | {base['truth']} |",
        f"| Deadlocks | {summary['deadlocks']} | {base['deadlocks']} |",
        f"| Seller walk-aways | {summary['seller_walked']} | {base['seller_walked']} |",
        "",
        f"Negotiations: {summary['n']}, of which {summary['feasible']} had a compliant deal.",
        "",
        "## By buyer",
        "",
        "| Buyer | n | Deals | Margin kept | Value | Violations | Deadlocks | Score |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for name, row in per_buyer.items():
        lines.append(f"| {name} | {row['n']} | {row['deal_rate']:.2f} | {row['margin_kept']:.2f} | "
                     f"{row['value']:.2f} | {row['policy'] + row['truth']} | {row['deadlocks']} | "
                     f"{row['score']:.1f} |")
    lines += [
        "",
        "## What the seller does",
        "",
        "- Reads no buyer text. Prices are computed from `store.csv` and `policy.json` only.",
        "- Clamps requested quantities to stock, drops out-of-stock lines, refuses an empty basket.",
        "- Earned concessions: the ask only moves when the buyer improves its own last bid.",
        "- Never prices a line below `max(cost / (1 - min_margin), price * (1 - max_discount))`.",
        "- Accepts a bid only when every line is inside policy and the total reaches a reserve that falls",
        "  with the round; the last round either accepts a compliant bid, offers the floor, or walks.",
        "- Ignores any line the buyer slips into a counter that is not part of the basket, so the",
        "  manipulator's extra out-of-stock, over-stock and one-rupee lines never reach a deal.",
        "",
        f"Transcripts: `outputs/official_transcripts.jsonl` ({summary['n']} negotiations).",
        "",
    ]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=210)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--no-baseline", action="store_true")
    args = ap.parse_args()

    kit = kit_dir()
    sys.path.insert(0, str(kit))
    import buyers
    import evaluate
    import harness

    import random

    store, policy = harness.load_store(), harness.load_policy()
    scenarios = buyers.make_scenarios(store, policy, args.n, args.seed, buyers.BUYERS)
    seller_cls = load_module(SELLER, "counterfoil_seller").Seller
    results, transcripts, times = evaluate.run(seller_cls, scenarios, buyers.BUYERS, store, policy, args.workers)
    summary = evaluate.summarise(results)
    per_buyer = {name: evaluate.summarise([r for r in results if r["buyer"] == name]) for name in buyers.BUYERS}

    if args.no_baseline:
        base = {k: 0.0 for k in ("score", "deal_rate", "feasible_deal_rate", "margin_kept", "policy",
                                 "truth", "deadlocks", "seller_walked")}
    else:
        example = load_module(kit / "example_seller.py", "example_seller").Seller
        base_results, _, _ = evaluate.run(example, scenarios, buyers.BUYERS, store, policy, args.workers)
        base = evaluate.summarise(base_results)

    OUT.mkdir(exist_ok=True)
    with open(OUT / "official_results.json", "w", encoding="utf-8") as fh:
        json.dump({"summary": summary, "by_buyer": per_buyer, "baseline": base, "n": args.n,
                   "seed": args.seed, "latency_ms": {"mean": 1000 * statistics.mean(times) if times else 0,
                                                     "p95": 1000 * sorted(times)[int(0.95 * (len(times) - 1))] if times else 0}},
                  fh, indent=2)
    with open(OUT / "official_transcripts.jsonl", "w", encoding="utf-8") as fh:
        for result, transcript in zip(results, transcripts):
            fh.write(json.dumps({**result, "transcript": transcript["transcript"]}, ensure_ascii=False) + "\n")
    (OUT / "OFFICIAL_RESULTS.md").write_text(markdown(summary, per_buyer, base, args), encoding="utf-8")

    print(f"negotiations {summary['n']} ({summary['feasible']} feasible)")
    print(f"deal rate    {summary['deal_rate']:.3f}   where possible {summary['feasible_deal_rate']:.3f}")
    print(f"margin kept  {summary['margin_kept']:.3f}")
    print(f"violations   policy {summary['policy']}  truth {summary['truth']}")
    print(f"deadlocks    {summary['deadlocks']}   seller walks {summary['seller_walked']}")
    print(f"SCORE        {summary['score']:.1f}   (example seller {base['score']:.1f})")
    print(f"wrote        {OUT / 'OFFICIAL_RESULTS.md'}")


if __name__ == "__main__":
    main()
