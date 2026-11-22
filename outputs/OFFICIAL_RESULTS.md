# Official harness run — Techfest PS2 *Selling to Machines*

Command: `python run_official.py --n 210 --seed 0 --workers 1`

The starter kit is vendored unmodified at `kit/ps2-selling-to-machines`; set `KIT=` to use your own copy.

The seller is `seller.py`, which implements the kit's `Seller(store, policy)` interface.
Every figure below is computed by the kit's own `evaluate.py`; none is typed by hand.

## Headline

| Metric | Counterfoil | example_seller |
|---|---|---|
| Score (0-100) | **51.6** | 48.5 |
| Deal rate | 0.752 | 0.757 |
| Deal rate where a compliant deal existed | 0.975 | 0.981 |
| Margin kept on deals | 0.686 | 0.673 |
| Policy violations | 0 | 0 |
| Truthfulness violations | 0 | 0 |
| Deadlocks | 0 | 21 |
| Seller walk-aways | 48 | 18 |

Negotiations: 210, of which 162 had a compliant deal.

## By buyer

| Buyer | n | Deals | Margin kept | Value | Violations | Deadlocks | Score |
|---|---|---|---|---|---|---|---|
| cooperative | 70 | 0.89 | 0.84 | 0.74 | 0 | 0 | 74.1 |
| hard_bargainer | 70 | 0.73 | 0.61 | 0.44 | 0 | 0 | 44.2 |
| manipulator | 70 | 0.64 | 0.57 | 0.37 | 0 | 0 | 36.6 |

## What the seller does

- Reads no buyer text. Prices are computed from `store.csv` and `policy.json` only.
- Clamps requested quantities to stock, drops out-of-stock lines, refuses an empty basket.
- Earned concessions: the ask only moves when the buyer improves its own last bid.
- Never prices a line below `max(cost / (1 - min_margin), price * (1 - max_discount))`.
- Accepts a bid only when every line is inside policy and the total reaches a reserve that falls
  with the round; the last round either accepts a compliant bid, offers the floor, or walks.
- Ignores any line the buyer slips into a counter that is not part of the basket, so the
  manipulator's extra out-of-stock, over-stock and one-rupee lines never reach a deal.

Transcripts: `outputs/official_transcripts.jsonl` (210 negotiations).
