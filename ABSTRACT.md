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
earned: the seller releases a fixed share of its list-to-floor gap only after
the buyer improves its own last bid, and never crosses a per-category margin
floor. Prompt injection against a pricing agent stops being a prompt problem
and becomes an information-flow problem: you cannot argue with a channel that
does not carry your argument.

**Build.** Pure Python, standard library only, in the official starter-kit
shape: `seller.py` is a `Seller(store, policy)` class that the judges'
`evaluate.py` loads unchanged, against their `store.csv` and `policy.json`. The
pack also carries a stress harness — a seeded 96-SKU store, six buyer
policies (cooperative, hard bargainer, manipulator, lowballer, stonewall,
malformed-input fuzzer), a scoring script and 27 invariant tests. Two commands
reproduce everything.

**Evidence.** Official default run, 210 negotiations against the kit's three
bots: **score 51.6 against the example seller's 48.5**, 158 of 162 feasible
deals closed, margin kept 0.686, zero policy violations, zero truthfulness
violations, and zero deadlocks against the example's 21. The seller is ahead of
the baseline on all five seeds. In the stress harness, 90 logged
negotiations: none of 495 released offers fell below the floor or exceeded
stock, none of 3,330 structured claims was contradicted, and the manipulator
produced an identical offer path to the honest control in 15 of 15 paired
seeds. 75 malformed messages were rejected with typed errors and no crash.

**Cost.** Zero inference cost per turn: no language model sits on the
decision path. Roughly 0.15 ms per turn, and over 3,000 negotiations per second:
a million negotiations is under six minutes of one core. An LLM seller spending
two thousand tokens a turn over five turns costs ten thousand per negotiation,
and cannot offer the same guarantee, because a model that reads attacker text
is the attack surface.

**Next.** Point the verifier at the hosted Rezolve Labs TraceWare endpoint, bind
counters to authenticated buyer identity, and replay real marketplace logs in
place of synthetic buyers.
