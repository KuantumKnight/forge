"""Box 4 — run the triage agent over one issue and write the verdict back.

Orchestration glue between the two D2 Lane A resources:

    issue row --> triage agent (read-only judge) --> normalize_priority (writer)

The agent emits ``{priority, repro_steps, reason}`` (strict JSON, via its
``final_result`` tool); ``normalize_priority`` coerces the priority to the enum and
stamps the row ``triaged``. This module just drives that round-trip per issue.

    .venv/Scripts/python.exe ingest/triage/run_triage.py gh_13571
"""

from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from pod.lemma_client import get_pod, load_env  # noqa: E402
from pod.tables.issues_table import TABLE_NAME  # noqa: E402

AGENT_NAME = "triage"
FUNCTION_NAME = "normalize_priority"

# Agent runs are async; poll the conversation until it settles.
_TERMINAL = {"COMPLETED", "FAILED", "STOPPED"}


def _status_str(conv) -> str:
    status = getattr(conv, "status", None)
    return getattr(status, "value", str(status)).upper()


def _build_prompt(issue: dict) -> str:
    return (
        "Triage this issue.\n"
        f"id: {issue['id']}\n"
        f"title: {issue.get('title', '')}\n"
        f"body: {issue.get('body', '') or '(no body provided)'}"
    )


def _extract_output(messages: list[dict]) -> dict:
    """Pull the agent's structured verdict out of a finished conversation.

    Primary source is the ``final_result`` tool message (schema-enforced); fall
    back to parsing the last assistant text as JSON.
    """
    # Walk newest-first so the latest verdict wins on a resumed conversation.
    for msg in reversed(messages):
        if msg.get("tool_name") == "final_result":
            for slot in ("tool_args", "tool_result"):
                payload = msg.get(slot) or {}
                if isinstance(payload, dict) and isinstance(payload.get("output"), dict):
                    return payload["output"]
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("text"):
            text = msg["text"].strip()
            if text.startswith("```"):
                text = text.strip("`")
                text = text[text.find("{"): text.rfind("}") + 1]
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                continue
    raise RuntimeError("triage agent produced no parseable verdict")


def run_agent(pod, issue: dict, timeout_s: int = 150, poll_s: float = 3.0) -> dict:
    """Run the triage agent over one issue; return its raw verdict dict."""
    conv = pod.agents.run(AGENT_NAME, _build_prompt(issue))
    conv_id = str(conv.id)

    deadline = time.monotonic() + timeout_s
    state = _status_str(conv)
    while state not in _TERMINAL and time.monotonic() < deadline:
        time.sleep(poll_s)
        state = _status_str(pod.conversations.get(conv_id))

    if state != "COMPLETED":
        raise RuntimeError(f"triage run {conv_id} ended in state {state!r}")

    messages = pod.conversations.messages(conv_id).to_dict().get("items", [])
    verdict = _extract_output(messages)
    verdict["_conversation_id"] = conv_id
    return verdict


def triage_one(pod, issue_id: str) -> dict:
    """Triage a single issue and write the result back via normalize_priority."""
    issue = pod.records.get(TABLE_NAME, issue_id)
    verdict = run_agent(pod, issue)

    result = pod.functions.run(
        FUNCTION_NAME,
        {
            "issue_id": issue_id,
            "priority": verdict.get("priority"),
            "repro_steps": verdict.get("repro_steps"),
            "reason": verdict.get("reason"),
        },
    )
    out = result.to_dict() if hasattr(result, "to_dict") else result
    written = out.get("output_data", out) if isinstance(out, dict) else out
    return {"issue_id": issue_id, "verdict": verdict, "written": written}


def list_untriaged(pod, limit: int = 200) -> list[dict]:
    """All newly-ingested issues awaiting triage (status == 'new')."""
    return pod.records.list(
        TABLE_NAME,
        limit=limit,
        filter=[{"field": "status", "op": "eq", "value": "new"}],
    ).to_dict().get("items", [])


def triage_batch(pod) -> dict:
    """Triage every newly-ingested issue. One failure never aborts the batch."""
    pending = list_untriaged(pod)
    print(f"triage batch: {len(pending)} new issue(s)")
    ok = failed = 0
    for issue in pending:
        issue_id = issue["id"]
        try:
            res = triage_one(pod, issue_id)
            w = res["written"] or {}
            print(f"  [ok] {issue_id} -> {w.get('priority')} (coerced={w.get('coerced')})")
            ok += 1
        except Exception as exc:  # keep going; the row stays 'new' for a retry
            print(f"  [skip] {issue_id}: {exc}")
            failed += 1
    return {"pending": len(pending), "triaged": ok, "failed": failed}


def main() -> int:
    load_env()
    pod = get_pod()
    if len(sys.argv) >= 2:
        issue_id = sys.argv[1]
        res = triage_one(pod, issue_id)
        w = res["written"] or {}
        print(
            f"PASS: triaged {issue_id} -> priority={w.get('priority')} "
            f"status={w.get('status')} coerced={w.get('coerced')}"
        )
        return 0
    stats = triage_batch(pod)
    print(
        f"PASS: batch triaged {stats['triaged']}/{stats['pending']} "
        f"({stats['failed']} skipped)"
    )
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
