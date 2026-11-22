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

Then I measured it on the judges' own code, not mine. My seller implements the
official starter kit's interface, and the kit's `evaluate.py` scores it 51.6
against 48.5 for the kit's own example seller over 210 negotiations — with zero
policy violations, zero truthfulness violations and zero deadlocks, where the
example deadlocks 21 times.

Then I broke it on purpose. Ninety more negotiations through my own stricter
protocol, against six buyer policies, one of which lies on every single turn
with fake competitor quotes, fake manager approval and a prompt injection. The
price path came out identical to the honest control on all fifteen paired
seeds. Zero of 495 offers went below the margin floor. And it runs at thousands
of negotiations per second because there is no model on the decision path.

## Resume bullets

Pick two. Do not use all three; three bullets for one project reads as padding.

- Built a policy-constrained seller agent for agent-to-agent commerce (Python,
  standard library only) that implements the official Techfest x Rezolve Labs
  harness interface and **scores 51.6 against the kit's 48.5 example seller** —
  158 of 162 feasible deals closed, 0 policy violations, 0 truthfulness
  violations, 0 deadlocks over 210 negotiations.
- Wrote an adversarial harness with six buyer policies; a bot injecting fake
  competitor quotes, fake manager approval and a policy-override instruction
  produced a bit-identical offer path to the honest control on 15 of 15 paired
  seeds, because buyer text is dropped before it can reach a number.
- Pinned both interfaces with 27 dependency-free invariant tests (16 stress,
  11 official-format) covering the floor, stock clamping, extra-line rejection
  and the final-round close-or-walk rule; one command regenerates every
  published figure from the transcripts.

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

Evidence is measured on the challenge's own scoring code: 210 official
negotiations score 51.6 against 48.5 for the starter kit's example seller, with
0 policy violations, 0 truthfulness violations and 0 deadlocks (the example
deadlocks 21 times). A separate 90-negotiation adversarial harness shows a
manipulation bot producing an identical price path to the honest control on all
15 paired seeds. Zero inference cost per turn.

Python, standard library only. `python run_official.py` and `python run_all.py`
reproduce every number.

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
2. `outputs/OFFICIAL_RESULTS.md` — the score against the judges' own harness.
3. `outputs/RESULTS.md` — the adversarial numbers, regenerated from transcripts.
4. `seller.py` — the official-format seller, and the only pricing logic in it.
5. `python -m src.demo --parity --seed 3` — the proof, in four seconds.

## Honest limits — keep these in the README, not hidden

- Buyer bots are synthetic. No real marketplace logs were used.
- The hosted Rezolve Labs verifier was not exercised without an API key; the
  offline reference verifier produced every published figure.
- The store is synthetic and seeded, so results are reproducible but not
  market-representative.
