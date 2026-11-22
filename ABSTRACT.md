# Counterfoil — a machine seller whose offers cannot be talked off the ledger

**Impact.** Agent-to-agent commerce is arriving: procurement bots, distributor
portals, marketplaces where the buyer is a program optimising for price. The
first generation of AI sales agent puts a language model directly on the price,
which creates two failures a retailer cannot ship. Margin leaks through
language — a buyer bot that invents a competitor quote, a manager approval, or
an expiring PO can talk a model down. And the agent asserts things it cannot
prove: "in stock", "list price was X", which becomes legal exposure the moment
the buyer is a machine that acts on it. Counterfoil removes both by removing
language from the decision path.

**Innovation.** The seller's authority is a policy engine over the store
ledger; free text is never parsed into a price. Every offer carries structured
claims — this SKU's list price, its stock, the bundle rate, the round — and a
verifier checks each one against the ledger before the offer is released. A
contradiction withholds the offer rather than shipping it. Concessions are
earned: the seller moves only when the buyer improves, by the smaller of a
fixed step and a share of the remaining gap, and never below a per-category
margin floor. Prompt injection against a pricing agent stops being a prompt
problem and becomes an information-flow problem: you cannot argue with a
channel that does not carry your argument.

**Build.** Pure Python standard library. A seeded 96-SKU store, a JSON policy
with per-category floors and caps, a turn-based negotiation protocol, six buyer
policies (cooperative, hard bargainer, manipulator, lowballer, stonewall,
malformed-input fuzzer), a harness that logs every message, an evaluator that
recomputes every figure from those logs, and sixteen invariant tests. Two
commands reproduce everything.

**Evidence.** 90 logged negotiations. None of the 495 released offers fell
below the margin floor or exceeded stock. None of the 3,330 structured claims
was contradicted by the store. The manipulator runs the hard bargainer's exact
arithmetic with adversarial text and produces an identical offer path, round
count and final price in 15 of 15 paired seeds. Seventy-five malformed messages
were rejected with typed errors and no crash. Deals closed 5% above the floor
against a determined buyer, 18% above against a cooperative one, and never
below against a buyer that anchors underneath it.

**Cost.** Zero inference cost per turn, because no language model sits on the
decision path. Over 2,500 negotiations per second on a single core: a million
negotiations is under seven minutes of one core. An LLM seller spending roughly
two thousand tokens a turn over five turns costs about ten thousand tokens per
negotiation, and cannot offer the same guarantee, because a model that reads
attacker text is the attack surface.

**Next.** Point the verifier at the hosted Rezolve Labs TraceWare endpoint, bind
counters to authenticated buyer identity, and replay real marketplace logs in
place of synthetic buyers.
