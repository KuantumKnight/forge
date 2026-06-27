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

from typing import Optional

from pydantic import BaseModel
from lemma_sdk import Pod

# The issues.status enum, kept in sync with docs/contracts.md §1.
VALID_STATUSES = {"new", "triaged", "investigating", "resolved"}


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
    pod.table("issues").update(data.issue_id, {"status": requested})

    return SetStatusResult(issue_id=data.issue_id, status=requested, ok=True)
