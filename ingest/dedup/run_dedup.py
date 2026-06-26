"""D3 Lane A driver — discover, confirm, and link duplicate issues.

Ties the three D3 resources together for one issue:

    find_similar (top-5) --> dedup_confirm (YES/NO on the top hit) --> link_related

Only the single top similarity hit is sent to the LLM (one confirm call per issue,
per the plan). A confirmed duplicate is linked symmetrically via link_related.

    .venv/Scripts/python.exe ingest/dedup/run_dedup.py iss_003   # one issue
    .venv/Scripts/python.exe ingest/dedup/run_dedup.py           # all iss_* feedback
"""

from __future__ import annotations

import pathlib
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pod.lemma_client import get_pod, load_env  # noqa: E402
from pod.tables.issues_table import TABLE_NAME  # noqa: E402
# Reuse the verified agent-run plumbing from the triage driver.
from ingest.triage.run_triage import _TERMINAL, _extract_output, _status_str  # noqa: E402

CONFIRM_AGENT = "dedup_confirm"
FIND_FN = "find_similar"
LINK_FN = "link_related"


def _fn_output(result) -> dict:
    out = result.to_dict() if hasattr(result, "to_dict") else result
    return out.get("output_data", out) if isinstance(out, dict) else out


def _confirm_prompt(a: dict, b: dict) -> str:
    return (
        "Are these two issue reports duplicates of the same underlying problem?\n\n"
        f"=== ISSUE A ({a['id']}, source={a.get('source')}) ===\n"
        f"title: {a.get('title', '')}\n"
        f"body: {a.get('body', '')}\n\n"
        f"=== ISSUE B ({b['id']}, source={b.get('source')}) ===\n"
        f"title: {b.get('title', '')}\n"
        f"body: {b.get('body', '')}"
    )


def _run_confirm(pod, a: dict, b: dict, timeout_s: int = 120, poll_s: float = 3.0) -> dict:
    conv = pod.agents.run(CONFIRM_AGENT, _confirm_prompt(a, b))
    cid = str(conv.id)
    deadline = time.monotonic() + timeout_s
    state = _status_str(conv)
    while state not in _TERMINAL and time.monotonic() < deadline:
        time.sleep(poll_s)
        state = _status_str(pod.conversations.get(cid))
    if state != "COMPLETED":
        raise RuntimeError(f"confirm run {cid} ended in state {state!r}")
    messages = pod.conversations.messages(cid).to_dict().get("items", [])
    return _extract_output(messages)


def dedup_one(pod, issue_id: str, min_score: float = 0.0, max_confirm: int = 3) -> dict:
    """Find similar issues, confirm candidates with the LLM, link the first duplicate.

    HYBRID ranking is rank-based and not always perfectly ordered — a semantically
    identical report in very different words (e.g. iss_025 "gh stops working every
    afternoon" vs gh_158 "401 after SSO session expiry") can sit behind a weaker
    lexical match. So we walk the top ``max_confirm`` candidates and let
    ``dedup_confirm`` (which errs toward NO) be the gate, instead of trusting rank #1
    alone. The first confirmed duplicate is linked; non-duplicates are rejected.
    """
    issue = pod.records.get(TABLE_NAME, issue_id)
    sim = _fn_output(pod.functions.run(FIND_FN, {"issue_id": issue_id, "top_k": 5}))
    candidates = [c for c in (sim or {}).get("candidates", []) if c["score"] >= min_score]
    if not candidates:
        return {"issue_id": issue_id, "linked": None, "reason": "no similar candidates"}

    checked = []
    for cand in candidates[:max_confirm]:
        other = pod.records.get(TABLE_NAME, cand["id"])
        verdict = _run_confirm(pod, issue, other)
        checked.append(cand["id"])
        if verdict.get("is_duplicate"):
            link = _fn_output(pod.functions.run(LINK_FN, {"id_a": issue_id, "id_b": cand["id"]}))
            return {"issue_id": issue_id, "candidate": cand["id"], "linked": cand["id"],
                    "reason": verdict.get("reason"), "link": link, "checked": checked}

    return {"issue_id": issue_id, "candidate": candidates[0]["id"], "linked": None,
            "reason": f"no duplicate among top {len(checked)} ({', '.join(checked)})",
            "checked": checked}


def _feedback_ids(pod) -> list[str]:
    """The cross-source chat feedback (iss_*) — what we dedup against the backlog."""
    items = pod.records.list(TABLE_NAME, limit=300).to_dict()["items"]
    return sorted(i["id"] for i in items if i["id"].startswith("iss_"))


def dedup_batch(pod, ids: list[str] | None = None) -> dict:
    ids = ids if ids is not None else _feedback_ids(pod)
    print(f"dedup batch: {len(ids)} issue(s)")
    linked = checked = failed = 0
    for iid in ids:
        try:
            r = dedup_one(pod, iid)
            checked += 1
            if r.get("linked"):
                linked += 1
                print(f"  [link] {iid} <-> {r['linked']}: {r.get('reason')}")
            else:
                print(f"  [no ] {iid} (cand={r.get('candidate')}): {r.get('reason')}")
        except Exception as exc:
            failed += 1
            print(f"  [skip] {iid}: {exc}")
    return {"checked": checked, "linked": linked, "failed": failed}


def main() -> int:
    load_env()
    pod = get_pod()
    if len(sys.argv) >= 2:
        print(f"PASS: {dedup_one(pod, sys.argv[1])}")
        return 0
    stats = dedup_batch(pod)
    print(
        f"PASS: dedup linked {stats['linked']} of {stats['checked']} checked "
        f"({stats['failed']} skipped)"
    )
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
