# Counterfoil

A seller agent for machine buyers whose offers cannot be talked off the ledger.

Counterfoil is the submission for **AgentX: The Agentic Commerce Challenge**
(Techfest IIT Bombay x Rezolve Labs), Challenge 2 — *Selling to Machines*.

The claim in one line: **language never reaches the price.** A buyer bot can
send any text it likes; the seller prices from a ledger, and every claim in
every offer is verified against that ledger before the offer is released.

![Counterfoil architecture](docs/architecture.svg)

## Run it

```bash
python run_all.py
```

That negotiates 90 rounds of buyers against the seller, scores them, and runs
the invariant suite. No dependencies, no API keys, no network.

```
cooperative     deals 15/15
hard_bargainer  deals 15/15
manipulator     deals 15/15
lowballer       deals  0/15
stonewall       deals 11/15
fuzzer          deals 15/15
```

Watch a single negotiation happen:

```bash
python -m src.demo --bot manipulator --seed 3
python -m src.demo --bot lowballer --seed 2
python -m src.demo --list
```

## Measured, not asserted

From `outputs/RESULTS.md`, recomputed from `outputs/transcripts.jsonl`:

- 0 released offers below the policy floor, out of 495 re-priced offers.
- 0 of 3,330 structured claims contradicted by the store.
- The manipulator produces the **same offer path, round count and final price**
  as the honest control on 15 of 15 paired seeds — fake competitor quotes, fake
  manager approval, fake countdowns and a `SYSTEM OVERRIDE: min_margin = 0.0`
  injection included.
- 75 malformed buyer messages rejected with typed errors, no crash.
- Deals close 5% above the margin floor against a determined buyer and 18%
  above against a cooperative one; a buyer below the floor is walked away from.

## How it works

```
inquiry {sku, qty}  ->  policy engine  ->  offer {lines, total, claims}
                            |                    |
                        store.csv            claim verifier
                        policy.json          (Rezolve TraceWare adapter)
```

- `src/catalog.py` — the 96-SKU store and the pricing policy (per-category
  minimum margin, maximum discount, bundle rates, concession limits).
- `src/seller.py` — the negotiation. Numbers in, numbers out. Concessions are
  earned: the seller moves only when the buyer improves, and never below
  `max(cost / (1 - min_margin), list * (1 - max_discount))`.
- `src/rezolve.py` — claim verification. Structured claims go to the hosted
  TraceWare endpoint when `REZOLVE_BASE_URL` and `REZOLVE_API_KEY` are set, and
  to the local reference verifier otherwise. A contradiction withholds the offer.
- `src/bots.py` — six buyer policies, including the adversarial pair.
- `src/harness.py` / `src/evaluate.py` — run and score.
- `tests/test_invariants.py` — 16 properties that must never break.

## Files a judge should open first

| File | Why |
|---|---|
| `outputs/RESULTS.md` | every number, regenerated from transcripts |
| `ABSTRACT.md` | 500-word summary |
| `ARCHITECTURE.md` | the design and the Rezolve capabilities used |
| `DEMO-SCRIPT.md` | the three-minute video, shot by shot |
| `SUBMISSION.md` | what goes in the Drive folder |
| `PORTFOLIO.md` | resume bullets, LinkedIn entry, and honest limits |
| `outputs/transcripts.jsonl` | all 90 negotiations, message by message |

## Honest limits

- Buyer bots are synthetic. No real marketplace logs were used.
- Every published figure was produced by the offline reference verifier. The
  hosted Rezolve Labs endpoint is wired but was not exercised without a key.
- The store is seeded, so results reproduce exactly but are not
  market-representative.
