# Portfolio notes

How to use this project to get interviews, without overstating it.

## One line

> A seller agent for machine buyers whose offers cannot be talked off the ledger:
> free text never reaches a price, and every claim in every offer is verified
> against the store before it ships.

## The 60-second version, out loud

Retail is about to get machine buyers — procurement bots and shopping agents
that optimise hard and will say anything. The interesting problem is not making
a model sound like a salesperson. It is making sure a bot that lies cannot move
your price.

So the seller's pricing authority is a policy engine over the store. Free text
never reaches a number — it is dropped at the type boundary. Each offer carries
structured claims about list price, stock and the bundle rate, and a verifier
checks every claim against the ledger before the offer is released. If one
contradicts, the offer is withheld.

Then I proved it rather than asserting it. Ninety logged negotiations against
six buyer policies, one of which lies on every single turn with fake competitor
quotes and a prompt injection. The price path came out identical to the honest
control on all fifteen paired seeds. Zero of 495 offers went below the margin
floor. And it runs at a few thousand negotiations per second because there is no
model on the decision path.

## Resume bullets

Pick two. Do not use all three; three bullets for one project reads as padding.

- Built a policy-constrained seller agent for agent-to-agent commerce (Python,
  standard library only) that prices from a ledger and verifies every claim
  before release — 0 of 495 published offers below the margin floor and 0 of
  3,330 structured claims contradicted across 90 logged negotiations.
- Wrote an adversarial evaluation harness with six buyer policies; a bot
  injecting fake competitor quotes, fake manager approval and a
  `SYSTEM OVERRIDE` prompt produced a bit-identical offer path to the honest
  control on 15 of 15 paired seeds.
- Hardened the negotiation protocol against malformed input — 75 invalid
  counters rejected with typed errors and zero crashes — and pinned the
  invariants with a 16-test dependency-free suite that runs in one command.

## LinkedIn project entry

**Title:** Counterfoil — a seller agent that cannot be talked off the ledger
**Description:**

Most "AI sales agent" demos put a language model on the price. That is two
problems: a buyer bot that invents a competitor quote can talk it down, and the
agent asserts things it cannot prove.

Counterfoil separates language from authority. Pricing is a deterministic policy
engine over the store; buyer text is dropped at the type boundary. Every offer
carries structured claims that a verifier checks against the ledger before
release, and a contradiction withholds the offer rather than shipping it.

Evidence is measured, not claimed: 90 logged negotiations, 0 offers below the
margin floor, 0 of 3,330 claims contradicted, and a manipulation bot whose
adversarial text produces an identical price path to the honest control on all
15 paired seeds. Zero inference cost per turn.

Python, standard library only. `python run_all.py` reproduces every number.

## Questions this invites, and the honest answers

**"Why not just use an LLM?"**
Because a model that reads attacker-controlled text is the attack surface. And
because with the model out of the decision path, the margin floor stops being a
hope and becomes a unit test. The cost argument is a side effect, not the
reason.

**"Isn't that just a rules engine?"**
The rules are the authority, not the whole agent. The agent is the protocol, the
state machine, the earned-concession policy, the adversarial harness and the
verification gate. A rules engine alone does not negotiate.

**"What would break it?"**
Three real answers, worth giving because they are true. Every number comes from
synthetic buyer policies, not real marketplace logs. Bundle discounts and
per-category floors can conflict on a badly seeded catalogue — the generator
asserts `floor <= list` to keep that impossible. And a genuinely new basket
shape can leave a line at its floor while others absorb the concession, which is
correct but look unbalanced.

**"What did you learn?"**
That robustness against manipulation is usually framed as a prompting problem
and is really an information-flow problem. Bound the channel and most of the
attack surface disappears without a single defensive prompt.

## What a recruiter should click

1. The README, top to bottom — 60 seconds.
2. `outputs/RESULTS.md` — the numbers, regenerated from transcripts.
3. `src/seller.py` — the only file with the pricing logic in it.
4. `python -m src.demo --parity --seed 3` — the proof, in four seconds.

## Honest limits — keep these in the README, not hidden

- Buyer bots are synthetic. No real marketplace logs were used.
- The hosted Rezolve Labs verifier was not exercised without an API key; the
  offline reference verifier produced every published figure.
- The store is synthetic and seeded, so results are reproducible but not
  market-representative.
