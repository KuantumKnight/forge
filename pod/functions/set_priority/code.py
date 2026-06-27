#input_type_name: SetPriorityInput
#output_type_name: SetPriorityResult
#function_name: set_priority

"""Operator override — set an issue's ``priority`` (docs/contracts.md §1).

Triage (``normalize_priority``) sets the AI's verdict; this is the granted writer
for the *human* override the App exposes in its three-dot menu. It validates
against the priority enum, writes the row, and appends a ``priority_changed`` row
to the ``events`` audit trail (with the before→after in ``detail``) so the timeline
records who changed what.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from lemma_sdk import Pod

# The issues.priority enum, kept in sync with docs/contracts.md §1.
VALID_PRIORITIES = {"critical", "high", "normal", "low"}


class SetPriorityInput(BaseModel):
    issue_id: str
    priority: str


class SetPriorityResult(BaseModel):
    issue_id: str
    priority: str          # the priority written
    ok: bool               # False if the requested priority was invalid (no write)
    error: Optional[str] = None


def _append_event(pod, issue_id, kind, actor, summary, detail=None):
    """Append one row to the ``events`` audit trail. Best-effort: a logging
    failure must never fail the override write the operator asked for."""
    try:
        pod.records.create("events", {
            "id": "evt_" + uuid.uuid4().hex,
            "issue_id": issue_id,
            "kind": kind,
            "actor": actor,
            "summary": summary,
            "detail": json.dumps(detail) if detail is not None else None,
            "ts": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        pass


async def set_priority(ctx, data: SetPriorityInput) -> SetPriorityResult:
    requested = (data.priority or "").strip().lower()
    if requested not in VALID_PRIORITIES:
        return SetPriorityResult(
            issue_id=data.issue_id,
            priority=requested,
            ok=False,
            error=f"invalid priority {data.priority!r}; expected one of {sorted(VALID_PRIORITIES)}",
        )

    pod = Pod.from_env()
    issues = pod.table("issues")
    previous = None
    try:
        row = issues.get(data.issue_id)
        previous = getattr(row, "priority", None) or (row.get("priority") if isinstance(row, dict) else None)
    except Exception:
        previous = None

    issues.update(data.issue_id, {"priority": requested})
    _append_event(
        pod, data.issue_id, "priority_changed", "operator",
        f"Priority changed to {requested.capitalize()}",
        {"from": previous, "to": requested},
    )

    return SetPriorityResult(issue_id=data.issue_id, priority=requested, ok=True)
