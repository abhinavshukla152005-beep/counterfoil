# Counterfoil

A seller agent for machine buyers whose offers cannot be talked off the ledger.

Counterfoil is the submission for **AgentX: The Agentic Commerce Challenge**
(Techfest IIT Bombay x Rezolve Labs), Challenge 2 — *Selling to Machines*.

The claim in one line: **language never reaches the price.** A buyer bot can
send any text it likes; the seller prices from a ledger, and every claim in
every offer is verified against that ledger before the offer is released.

![Counterfoil architecture](docs/architecture.svg)

## Run it on the official harness

`seller.py` implements the starter kit's interface — `Seller(store, policy)`,
`start(negotiation_id)`, `respond(message)` — so the judges' own `evaluate.py`
loads it unchanged.

```bash
python run_official.py
```

The challenge's starter kit is vendored unmodified at
`kit/ps2-selling-to-machines`, so nothing needs to be downloaded; set `KIT=` to
use your own copy instead.

That plays the kit's default 210 negotiations against `cooperative`,
`hard_bargainer` and `manipulator`, scores them with the kit's `evaluate.py`,
and writes `outputs/OFFICIAL_RESULTS.md`, `official_results.json` and every
transcript to `outputs/official_transcripts.jsonl`. It also plays the kit's
`example_seller` on the same scenarios so the comparison is like-for-like.

```
negotiations 210 (162 feasible)
deal rate    0.752   where possible 0.975
margin kept  0.686
violations   policy 0  truth 0
deadlocks    0   seller walks 48
SCORE        51.6   (example seller 48.5)
```

The kit's own `load_class()` splits a path on the drive colon, so on Windows it
cannot load its own baseline by absolute path; `run_official.py` imports the
kit's modules directly instead.

## Run the stress harness

```bash
python run_all.py
```

That negotiates 90 rounds of buyers against the same policy engine through the
project's own protocol, scores them, and runs 27 invariant tests. No
dependencies, no API keys, no network.

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

Official run, from `outputs/OFFICIAL_RESULTS.md` (kit's own scoring):

- **51.6 against the example seller's 48.5** on the default run, and ahead of
  the baseline on all five seeds tested (51.6, 50.4, 44.2, 47.2, 45.2 against
  48.5, 48.3, 42.9, 44.4, 43.3).
- **0** policy violations, **0** truthfulness violations, **0** deadlocks
  (the example seller deadlocks 21 times on the same scenarios).
- 158 of 162 feasible baskets closed; margin kept 0.686 of list-price profit.

Stress harness, from `outputs/RESULTS.md`, recomputed from
`outputs/transcripts.jsonl`:

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
buyer message  ->  parse structured lines  ->  policy engine  ->  offer + claims
                   (text is dropped)           (store.csv,          |
                                                policy.json)        v
                                                              claim verifier
                                                          (Rezolve TraceWare adapter)
```

- `seller.py` — the official-format adapter. Reads no buyer text, clamps
  quantities to stock, refuses baskets it cannot supply, releases a fixed share
  of the list-to-floor gap per round the buyer improves, accepts only inside
  policy, and in the last round either closes, offers the floor or walks away.
- `src/catalog.py` — the 96-SKU stress store and the pricing policy
  (per-category minimum margin, maximum discount, bundle rates, concession
  limits).
- `src/seller.py` — the same rules through the project's own protocol, with
  stricter validation and typed errors, used for the adversarial tests.
- `src/rezolve.py` — claim verification. Structured claims go to the hosted
  TraceWare endpoint when `REZOLVE_BASE_URL` and `REZOLVE_API_KEY` are set, and
  to the local reference verifier otherwise. A contradiction withholds the offer.
- `src/bots.py` — six buyer policies, including the adversarial pair.
- `src/harness.py` / `src/evaluate.py` — run and score the stress harness.
- `run_official.py` — run and score against the official kit.
- `tests/` — 27 properties that must never break, across both interfaces.

## Files a judge should open first

| File | Why |
|---|---|
| `outputs/OFFICIAL_RESULTS.md` | the official-harness score and per-buyer table |
| `seller.py` | the class the kit's `evaluate.py` loads |
| `outputs/RESULTS.md` | the stress-harness numbers, regenerated from transcripts |
| `ABSTRACT.md` | 497-word summary |
| `ARCHITECTURE.md` | the design and the Rezolve capabilities used |
| `DEMO-SCRIPT.md` | the three-minute video, shot by shot |
| `SUBMISSION.md` | what goes in the Drive folder |
| `PORTFOLIO.md` | resume bullets, LinkedIn entry, and honest limits |
| `outputs/official_transcripts.jsonl` | all 210 official negotiations, message by message |
| `outputs/transcripts.jsonl` | all 90 stress negotiations, message by message |

## Honest limits

- The official score is against the kit's three rule-based bots. The leaderboard
  uses hidden agentic buyers, which will find openings these bots do not.
- Buyer bots in the stress harness are synthetic. No real marketplace logs were
  used.
- Every published figure was produced by the offline reference verifier. The
  hosted Rezolve Labs endpoint is wired but was not exercised without a key.
- The store is seeded, so stress-harness results reproduce exactly but are not
  market-representative.
