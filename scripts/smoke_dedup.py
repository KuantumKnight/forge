"""D3 box 4 — verify dedup catches the known seeded duplicate pairs.

Runs the dedup batch over the iss_* feedback, then asserts every known STRONG
duplicate pair is linked symmetrically (each row's related_ids contains the
other). Reports precision observations (the weak/thematic pair that should be
rejected, and the no-duplicate feedback that should stay unlinked) without
failing on them.

    .venv/Scripts/python.exe scripts/smoke_dedup.py
"""

from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pod.lemma_client import get_pod, load_env  # noqa: E402
from pod.tables.issues_table import TABLE_NAME  # noqa: E402
from ingest.dedup.run_dedup import dedup_batch  # noqa: E402

# Ground truth from seed/issues.json — genuine same-root-cause pairs.
STRONG_PAIRS = [
    ("gh_142", "iss_003"),  # gh pr create nil-pointer panic, no upstream remote
    ("gh_158", "iss_007"),  # 401 after SSO session expiry
    ("gh_171", "iss_011"),  # gh repo clone hangs behind corporate proxy
    ("gh_192", "iss_023"),  # Windows mojibake / non-UTF-8 issue titles
    ("gh_209", "iss_022"),  # gh release upload silent failure on name collision
]
# Weak/thematic pair that a precise confirm step SHOULD reject (same command,
# different bug): gh_201 (rate-limit backoff) vs iss_021 (debug header omission).
WEAK_PAIR = ("gh_201", "iss_021")
# Feedback with no genuine duplicate in the backlog — should stay unlinked.
NO_DUP = ["iss_015", "iss_018"]


def _related(pod, issue_id: str) -> list[str]:
    return pod.records.get(TABLE_NAME, issue_id).get("related_ids") or []


def main() -> int:
    load_env()
    pod = get_pod()

    # Run discovery + confirm + link over the feedback (idempotent).
    dedup_batch(pod)

    print("\n=== verification ===")
    failed = False

    for gh_id, iss_id in STRONG_PAIRS:
        a, b = _related(pod, gh_id), _related(pod, iss_id)
        ok = iss_id in a and gh_id in b
        print(f"{'PASS' if ok else 'FAIL'} strong pair {gh_id} <-> {iss_id} "
              f"(a={a}, b={b})")
        failed = failed or not ok

    # Precision observations — reported, not asserted.
    gh_w, iss_w = WEAK_PAIR
    linked_w = iss_w in _related(pod, gh_w)
    print(f"INFO weak pair {gh_w} <-> {iss_w}: "
          f"{'linked (false positive)' if linked_w else 'correctly NOT linked'}")
    for iid in NO_DUP:
        rel = _related(pod, iid)
        print(f"INFO no-dup {iid}: related_ids={rel} "
              f"{'(unexpected link)' if rel else '(clean)'}")

    print("DEDUP SMOKE PASS" if not failed else "DEDUP SMOKE FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
