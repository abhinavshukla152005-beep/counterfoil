# Submission pack

**AgentX: The Agentic Commerce Challenge** — Techfest IIT Bombay x Rezolve Labs.
Challenge 2, *Selling to Machines*. Round 1 closes **30 Nov 2026, 23:59 IST**.

## What Round 1 asks for, and where it is

| Requirement | File / action | Status |
|---|---|---|
| Abstract, max 500 words — impact, cost estimate, innovation, build summary | `ABSTRACT.md` (488 words) | done |
| 3-minute demo video | `DEMO-SCRIPT.md` — you record it | **yours** |
| Code repository and outputs on the public dev set | this folder + `outputs/` | done, needs publishing |
| List of Rezolve Labs capabilities used | `ARCHITECTURE.md`, section *Rezolve Labs capabilities used* | done |

## The three things only you can do

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

## Drive folder to upload

One folder, this layout, link pasted into the form's *Submission Link* field.
Google Drive links must be set to "anyone with the link can view" or judges
will get a request screen instead of the files.

```
Counterfoil-AgentX/
├── ABSTRACT.md
├── README.md
├── ARCHITECTURE.md
├── DEMO-SCRIPT.md
├── SUBMISSION.md
├── PORTFOLIO.md
├── docs/architecture.svg
├── policy.json
├── store.csv
├── run_all.py
├── src/                     catalog, seller, bots, rezolve, harness, evaluate, demo
├── tests/test_invariants.py
└── outputs/
    ├── RESULTS.md           the scored report
    ├── transcripts.jsonl    all 90 negotiations, message by message
    └── summary.json         per-policy roll-up
```

If you also publish a public repository (GitHub), put that URL in the form
too — a browsable repo plus a Drive folder is stronger than either alone.
Exclude `__pycache__/` and `.venv/`.

## Verify before you submit

```bash
python run_all.py
```

Expect `16/16 passed` and `RESULTS.md written; invariants OK`. If either fails,
do not submit — the failure is real.

## What the numbers will say

Pull these from `outputs/RESULTS.md` at submission time rather than from this
file, because they regenerate:

- offers released and re-priced from the store
- offers below the floor: must be 0
- claims contradicted: must be 0
- manipulator parity: must be n/n
- malformed messages handled

## Honest scope, stated up front

Worth saying plainly in the form's notes field, because a judge will notice it:

- The seller is a deterministic policy engine, not an LLM. That is the design,
  not a shortcut — it is what makes the floor invariant and the manipulation
  resistance testable rather than probabilistic. No model is on the decision
  path, so inference cost per turn is zero.
- Every figure in `RESULTS.md` comes from synthetic buyer policies in
  `src/bots.py`. No real marketplace logs were used.
- The claim verifier ran in `local-reference` mode unless a Rezolve key was
  configured. Both implementations satisfy the same contract and the test suite
  exercises the contract, not the transport.
