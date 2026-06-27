#input_type_name: SetStatusInput
#output_type_name: SetStatusResult
#function_name: set_status

"""Write an issue's lifecycle ``status`` (docs/contracts.md §1).

The status lifecycle is ``new -> triaged -> investigating -> resolved``. Triage
(``normalize_priority``) stamps ``triaged`` automatically; this function is the
granted writer for the operator-driven transitions the App exposes — chiefly
"mark resolved" (and re-open). It validates against the enum so a bad value never
reaches the table.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from lemma_sdk import Pod

# The issues.status enum, kept in sync with docs/contracts.md §1.
VALID_STATUSES = {"new", "triaged", "investigating", "resolved"}


def _append_event(pod, issue_id, kind, actor, summary, detail=None):
    """Append one row to the ``events`` audit trail. Best-effort: a logging
    failure must never fail the status write the operator asked for."""
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


class SetStatusInput(BaseModel):
    issue_id: str
    status: str


class SetStatusResult(BaseModel):
    issue_id: str
    status: str            # the status written
    ok: bool               # False if the requested status was invalid (no write)
    error: Optional[str] = None


async def set_status(ctx, data: SetStatusInput) -> SetStatusResult:
    requested = (data.status or "").strip().lower()
    if requested not in VALID_STATUSES:
        return SetStatusResult(
            issue_id=data.issue_id,
            status=requested,
            ok=False,
            error=f"invalid status {data.status!r}; expected one of {sorted(VALID_STATUSES)}",
        )

    pod = Pod.from_env()
    issues = pod.table("issues")
    previous = None
    try:
        row = issues.get(data.issue_id)
        previous = getattr(row, "status", None) or (row.get("status") if isinstance(row, dict) else None)
    except Exception:
        previous = None

    issues.update(data.issue_id, {"status": requested})
    _append_event(
        pod, data.issue_id, "status_changed", "operator",
        f"Status changed to {requested.capitalize()}",
        {"from": previous, "to": requested},
    )

    return SetStatusResult(issue_id=data.issue_id, status=requested, ok=True)
