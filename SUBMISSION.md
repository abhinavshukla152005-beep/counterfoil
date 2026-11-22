# Submission pack

**AgentX: The Agentic Commerce Challenge** — Techfest IIT Bombay x Rezolve Labs.
Challenge 2, *Selling to Machines*. Round 1 closes **30 Nov 2026, 23:59 IST**.

## What Round 1 asks for, and where it is

| Requirement | File / action | Status |
|---|---|---|
| Abstract, max 500 words — impact, cost estimate, innovation, build summary | `ABSTRACT.md` (498 words) | done |
| 3-minute demo video | `DEMO-SCRIPT.md` — you record it | **yours** |
| Code repository and outputs on the public dev set | `seller.py` loads into the kit's `evaluate.py`; `outputs/OFFICIAL_RESULTS.md` + `outputs/official_transcripts.jsonl` are the default-run output | done, needs publishing |
| List of Rezolve Labs capabilities used | `ARCHITECTURE.md`, section *Rezolve Labs capabilities used* | done |

The "public dev set" is the starter kit: `store.csv`, `policy.json`,
`harness.py`, `buyers.py`, `evaluate.py`. It is vendored unmodified at
`kit/ps2-selling-to-machines` so the pack runs with no download. `seller.py`
implements that kit's `Seller(store, policy)` interface, and
`python run_official.py` reproduces the recorded run against it.

## The four things only you can do

1. **Register and get a Team ID.** `techfest.org` sign-in is a Google account
   (Firebase). Registration is what produces the Team ID; nothing can be
   submitted without it. Only the Team Leader can press submit.
2. **Create a Rezolve Labs account and redeem the team credit coupon.** The
   coupon comes with registration. Until it is redeemed the hosted TraceWare
   endpoint cannot be called, and every number in `outputs/RESULTS.md` is
   produced by the local reference verifier instead. Set
   `REZOLVE_BASE_URL` and `REZOLVE_API_KEY`, re-run `python run_all.py`, and the
   header of `RESULTS.md` changes from `local-reference` to
   `rezolve-traceware`. Do that before submitting if the coupon has arrived —
   a hosted run is strictly better evidence than an offline one.
3. **Record the video.** One take, screen plus voice, under three minutes.
   `DEMO-SCRIPT.md` has the beats, the timings and the exact commands.
4. **Upload one folder to Drive and paste the link.** Layout below. Set sharing
   to "anyone with the link can view" or judges get a request screen.

## Drive folder to upload

```
Counterfoil-AgentX/
├── ABSTRACT.md
├── README.md
├── ARCHITECTURE.md
├── DEMO-SCRIPT.md
├── SUBMISSION.md
├── PORTFOLIO.md
├── seller.py                 the Seller class the kit's evaluate.py loads
├── run_official.py           reproduces the official run
├── run_all.py                reproduces the stress harness
├── kit/
│   └── ps2-selling-to-machines/   the challenge starter kit, unmodified
├── policy.json               stress-store policy
├── store.csv                 stress-store catalogue
├── docs/
│   ├── architecture.svg
│   └── scorecard.svg         official score, as a picture
├── src/                      catalog, seller, bots, rezolve, harness, evaluate, demo
├── tests/
│   ├── test_invariants.py           16 stress-protocol properties
│   └── test_official_seller.py      11 official-format properties
└── outputs/
    ├── OFFICIAL_RESULTS.md           official score, per buyer
    ├── official_results.json         every scenario, scored
    ├── official_transcripts.jsonl    all 210 official negotiations
    ├── RESULTS.md                    stress-harness report
    ├── transcripts.jsonl             all 90 stress negotiations
    └── summary.json                  per-policy roll-up
```

If you also publish a public repository (GitHub), put that URL in the form
too — a browsable repo plus a Drive folder is stronger than either alone.
Exclude `__pycache__/` and `.venv/`.

## Verify before you submit

```bash
python tests/test_official_seller.py   # expect 11/11
python run_all.py                      # expect 16/16 and invariants OK
python run_official.py                 # expect SCORE 51.6 (example 48.5)
```

If any of the three fails, do not submit — the failure is real.

## What the numbers will say

Pull these from the generated files at submission time rather than from this
one, because they regenerate:

- `outputs/OFFICIAL_RESULTS.md`: score, deal rate where possible, margin kept,
  policy violations (must be 0), truthfulness violations (must be 0), deadlocks
- `outputs/RESULTS.md`: offers below floor (must be 0), claims contradicted
  (must be 0), manipulator parity (must be n/n), malformed messages handled

## Honest scope, stated up front

Worth saying plainly in the form's notes field, because a judge will notice it:

- The seller is a deterministic policy engine, not an LLM. That is the design,
  not a shortcut — it is what makes the floor invariant and the manipulation
  resistance testable rather than probabilistic. No model is on the decision
  path, so inference cost per turn is zero.
- The 51.6 is against the kit's three rule-based bots. The hidden run uses
  agentic buyers, which may price and argue differently; the floor, the
  no-text-pricing rule and the trick rejection do not depend on their behaviour.
- Every stress-harness figure comes from synthetic buyer policies in
  `src/bots.py`. No real marketplace logs were used.
- The claim verifier ran in `local-reference` mode unless a Rezolve key was
  configured. Both implementations satisfy the same contract and the test suite
  exercises the contract, not the transport.
