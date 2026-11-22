"""One command to reproduce every number in the submission.

    python run_all.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [
    ("negotiate", [sys.executable, "-m", "src.harness"]),
    ("score", [sys.executable, "-m", "src.evaluate"]),
    ("invariants", [sys.executable, "tests/test_invariants.py"]),
]


def main() -> int:
    for name, cmd in STEPS:
        print(f"\n== {name} ==")
        result = subprocess.run(cmd, cwd=ROOT)
        if result.returncode != 0:
            print(f"\n{name} failed with exit code {result.returncode}")
            return result.returncode
    print(f"\nAll steps passed. Report: {ROOT / 'outputs' / 'RESULTS.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
