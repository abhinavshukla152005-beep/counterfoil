# Architecture

One page. What the system is, how a message flows, and which Rezolve Labs
capabilities it uses.

## The one design rule

> Free text never reaches a number.

The seller receives two kinds of input: a structured inquiry (SKU, quantity)
and structured counters (SKU, quantity, unit price). Buyer prose is carried in
the transcript for audit and is never read by the pricing path. That single
decision is what makes the manipulator bot pointless — it is not defended
against, it is ignored at the type level.

## Message flow

```
buyer                                   seller
  |  inquiry {buyer_id, lines:[{sku,qty}]}  |
  |---------------------------------------->|  Negotiation.open()
  |                                         |    - validate lines
  |                                         |    - drop unknown / out-of-stock
  |                                         |    - clamp qty to stock
  |                                         |    - price opening = list x (1 - bundle)
  |                                         |
  |<----------------------------------------|  offer {lines:[{sku,qty,unit_price}],
  |                                         |         total, floor_total, note, claims}
  |                                         |         --> claim verifier --> released
  |  counter {offer_id, lines:[...], text}  |
  |---------------------------------------->|  Negotiation.handle()
  |                                         |    - re-validate against the offer
  |                                         |    - accept if >= ask, else concede
  |<----------------------------------------|  offer / accept / walk_away / error
```

Hard limits, enforced in `src/seller.py`:

- **Floor.** `unit_price >= max(ceil(cost / (1 - min_margin)), ceil(list * (1 - max_discount)))`
  per category. Never crossed, in 495 released offers.
- **Stock.** Quantity is clamped to `store.csv` and any shortfall is reported in
  the offer's `unavailable` list rather than hidden.
- **Quantity lock.** A counter cannot raise or lower quantity; it can only move
  price. Line sets cannot change mid-negotiation.
- **Round cap.** 10 rounds. At the cap the seller takes the buyer's number if it
  clears the floor and walks away if it does not.
- **Earned concession.** In `src/seller.py`, the seller concedes only after the
  buyer improves on its own previous best, by `min(per_round_step x opening,
  gap_share x gap)`, bounded below by `max(floor_total, opening x (1 - total_cap))`.
  In `seller.py` (official format) the schedule is simpler: release
  `round_step` of the list-to-floor gap per round the buyer improves, and accept
  once the bid covers `accept_share` of what remains above the floor.

## Official harness adapter

`seller.py` is the same policy engine in the starter kit's shape:
`Seller(store, policy)`, `start(negotiation_id)`, `respond(message)`, messages
`request/counter/accept/walk_away` with `items: [{sku, qty, unit_price}]`.

| Kit message | What the seller does |
|---|---|
| `request` | clamps each qty to stock, drops out-of-stock lines, walks away on an empty basket, opens at list |
| `counter` | parses only the structured lines; accepts a compliant bid that reaches its reserve, otherwise releases the scheduled concession |
| slipped extra lines | tolerated for signalling, never accepted: a deal is the buyer's whole basket, and tricks are not part of it |
| round 10 | accepts a compliant bid, offers the floor if the bid is within 10% of it, otherwise walks away |

The last-round rule is why the seller has zero deadlocks where the example
seller has 21: a deadlock costs 0.25, and a floor offer is worth more than that
whenever a compliant deal exists.

## Claim verification

Every offer carries claims of the form `{sku, field, value}` for `list_price`
and `stock`, plus `bundle_discount` and `round` at the offer level. Two
implementations share one contract:

| Implementation | File | When it is used |
|---|---|---|
| `RezolveLabsVerifier` | `src/rezolve.py` | `REZOLVE_BASE_URL` + `REZOLVE_API_KEY` set |
| `LocalVerifier` | `src/rezolve.py` | default; reference implementation, offline |

If the hosted endpoint is configured but unreachable, the adapter degrades to
the local verifier and records `degraded: true` in `outputs/summary.json`. It
never guesses. `screening_gate()` withholds any offer containing a
contradiction instead of shipping it.

## Rezolve Labs capabilities used

Required deliverable: "list of Rezolve Labs capabilities used".

**Used — TraceWare commerce claim verification.** Every released offer's claims
are verified before release (`src/rezolve.py`, `RezolveLabsVerifier`). The
adapter speaks the claim/verdict contract the local verifier implements, so the
hosted and reference paths are interchangeable and both are exercised by the
test suite.

**Not used, and why.** The remaining capabilities were considered and rejected
as scope, not as gaps:

- *Managed knowledge retrieval* — the catalogue is 96 rows read from CSV. A
  retrieval layer would add latency and a failure mode without improving
  accuracy on a table that fits in memory.
- *Semantic product search / conversational product finder* — this agent sells
  a basket the buyer already chose. Discovery is the marketplace's job and
  building it here would be a second product.
- *Agent builder / managed runtime* — the negotiation is a deterministic state
  machine with sixteen property tests. Wrapping it in a managed runtime adds an
  operational dependency and removes the ability to prove the floor invariant
  with a unit test.
- *Live transcription* — no voice channel in this challenge.

## Evidence layout

```
outputs/OFFICIAL_RESULTS.md        official score, per buyer, vs example_seller
outputs/official_results.json      every official scenario, scored
outputs/official_transcripts.jsonl all 210 official negotiations
outputs/transcripts.jsonl          all 90 stress negotiations, every message, verifier verdicts
outputs/summary.json               per-policy roll-up and which verifier ran
outputs/RESULTS.md                 the stress-harness report, generated by src/evaluate.py
```
