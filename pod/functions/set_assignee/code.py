#input_type_name: SetAssigneeInput
#output_type_name: SetAssigneeResult
#function_name: set_assignee

"""Operator override — set an issue's ``assignee`` (docs/contracts.md §1).

The granted writer for the *human* "assign" control in the App's three-dot menu.
An empty/whitespace assignee clears the field (back to Unassigned). Writes the row
and appends an ``assignee_changed`` row to the ``events`` audit trail.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from lemma_sdk import Pod


class SetAssigneeInput(BaseModel):
    issue_id: str
    assignee: Optional[str] = None


class SetAssigneeResult(BaseModel):
    issue_id: str
    assignee: Optional[str] = None   # the value written (null = Unassigned)
    ok: bool
    error: Optional[str] = None


def _append_event(pod, issue_id, kind, actor, summary, detail=None):
    """Append one row to the ``events`` audit trail. Best-effort."""
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


async def set_assignee(ctx, data: SetAssigneeInput) -> SetAssigneeResult:
    # Normalize: empty / whitespace -> None (Unassigned).
    assignee = (data.assignee or "").strip() or None

    pod = Pod.from_env()
    issues = pod.table("issues")
    previous = None
    try:
        row = issues.get(data.issue_id)
        previous = getattr(row, "assignee", None) or (row.get("assignee") if isinstance(row, dict) else None)
    except Exception:
        previous = None

    issues.update(data.issue_id, {"assignee": assignee})
    summary = f"Assigned to {assignee}" if assignee else "Unassigned"
    _append_event(
        pod, data.issue_id, "assignee_changed", "operator",
        summary, {"from": previous, "to": assignee},
    )

    return SetAssigneeResult(issue_id=data.issue_id, assignee=assignee, ok=True)
