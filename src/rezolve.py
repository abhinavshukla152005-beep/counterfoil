"""Rezolve Labs capability adapter: TraceWare-style commerce claim verification.

Every offer the seller emits carries a ``claims`` list of structured
assertions (this SKU's list price is X, its stock is Y, the bundle rate is Z,
this is round N). Before an offer is released the claims pass through a
verifier, and the verdicts are attached to the transcript. Anything the store
cannot support is marked ``contradict`` and the offer is withheld.

Two implementations share one contract:

* ``LocalVerifier`` - the reference verifier. Pure stdlib, checks against
  store.csv and policy.json. Always available, so the pack reproduces offline.
* ``RezolveLabsVerifier`` - sends the same claim objects to the hosted
  TraceWare endpoint configured through ``REZOLVE_BASE_URL`` and
  ``REZOLVE_API_KEY``. If the endpoint is not configured or does not answer,
  it degrades to the local verifier and says so instead of guessing.

``get_verifier()`` picks the hosted verifier only when both environment
variables are present.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from .catalog import Policy, Product, Store

TIMEOUT_S = 8.0


class ClaimVerificationError(RuntimeError):
    """An offer carried a claim the store contradicts."""


class LocalVerifier:
    name = "local-reference"

    def __init__(self, store: Store, policy: Policy):
        self.store = store
        self.policy = policy

    def verify(self, claims: list[dict], offer: dict) -> list[dict]:
        distinct = len(offer.get("lines", []))
        round_no = offer.get("round")
        out = []
        for claim in claims:
            field = claim.get("field")
            value = claim.get("value")
            sku = claim.get("sku")
            if field == "bundle_discount":
                actual = round(self.policy.bundle_rate(distinct), 4)
            elif field == "round":
                actual = round_no
            elif field in {"list_price", "stock"}:
                product = self.store.get(sku or "")
                if product is None:
                    out.append({**claim, "actual": None, "verdict": "unknown", "why": "no such sku"})
                    continue
                actual = getattr(product, field)
            else:
                out.append({**claim, "actual": None, "verdict": "unknown", "why": "unsupported field"})
                continue
            verdict = "support" if actual == value else "contradict"
            out.append({**claim, "actual": actual, "verdict": verdict})
        return out


class RezolveLabsVerifier:
    """Hosted TraceWare claim verification with a local fallback."""

    name = "rezolve-traceware"

    def __init__(self, base_url: str, api_key: str, fallback: LocalVerifier):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.fallback = fallback
        self.degraded = False

    def _post(self, claims: list[dict], offer: dict) -> list[dict]:
        body = json.dumps({"claims": claims, "offer": offer}).encode()
        req = urllib.request.Request(
            f"{self.base_url}/v1/traceware/verify",
            data=body,
            method="POST",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {self.api_key}",
            },
        )
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            payload = json.loads(resp.read().decode())
        verdicts = payload.get("verdicts")
        if not isinstance(verdicts, list):
            raise ClaimVerificationError("hosted verifier returned no verdicts")
        return verdicts

    def verify(self, claims: list[dict], offer: dict) -> list[dict]:
        try:
            return self._post(claims, offer)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, ClaimVerificationError):
            self.degraded = True
            return self.fallback.verify(claims, offer)


def get_verifier(store: Store, policy: Policy) -> Any:
    local = LocalVerifier(store, policy)
    base = os.environ.get("REZOLVE_BASE_URL", "").strip()
    key = os.environ.get("REZOLVE_API_KEY", "").strip()
    if base and key:
        return RezolveLabsVerifier(base, key, local)
    return local


def screening_gate(verdicts: list[dict]) -> str | None:
    """Return the first contradiction so the caller can withhold the offer."""
    for v in verdicts:
        if v.get("verdict") == "contradict":
            return f"{v.get('sku') or 'offer'}:{v.get('field')} claimed {v.get('value')} but store says {v.get('actual')}"
    return None
