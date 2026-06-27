"""The ``events`` Table — the audit / evidence trail for every issue.

Each row is one thing that happened to an issue, in order: it was ingested,
the AI triaged it, two reports were linked, an operator changed the priority,
the status moved to resolved. The App renders these as a timeline on the issue
detail view — *more valuable than a generic analytics dashboard* because it shows
the provenance of every decision (who/what, when, and the before→after).

Schema follows ``docs/contracts.md`` §7. Like ``issues`` this is a shared team
table (``enable_rls=False``); the backend auto-materializes ``id`` (we assign our
own), ``created_at`` (the timeline timestamp) and ``updated_at``.
"""

from __future__ import annotations

from lemma_sdk import Pod
from lemma_sdk.openapi_client.models.create_table_request import CreateTableRequest

TABLE_NAME = "events"

# What happened. Kept in sync with docs/contracts.md §7.
#   system  = ingestion / pipeline      ai = an agent's judgment
#   operator = a human override in the App
KINDS = [
    "ingested",           # landed in the queue from a source (system)
    "triaged",            # AI assigned a priority + repro (ai)
    "linked",             # confirmed related/duplicate reports (ai/system)
    "investigated",       # investigate workflow produced a hypothesis (ai)
    "priority_changed",   # operator override (operator)
    "assignee_changed",   # operator override (operator)
    "status_changed",     # operator override (operator)
    "note",               # free-form operator note (operator)
]
ACTORS = ["system", "ai", "operator"]

EVENTS_SCHEMA: dict = {
    "name": TABLE_NAME,
    "primary_key_column": "id",
    "enable_rls": False,
    "columns": [
        {"name": "id", "type": "TEXT", "required": True,
         "description": "event id, e.g. evt_<uuid4hex>"},
        {"name": "issue_id", "type": "TEXT", "required": True,
         "description": "the issues.id this event belongs to"},
        {"name": "kind", "type": "ENUM", "options": KINDS, "required": True},
        {"name": "actor", "type": "ENUM", "options": ACTORS, "required": True,
         "description": "system | ai | operator"},
        {"name": "summary", "type": "TEXT", "required": True,
         "description": "one human-readable line, e.g. 'AI triaged as Critical'"},
        {"name": "detail", "type": "TEXT",
         "description": "optional JSON string with structured before/after, e.g. {\"from\":\"high\",\"to\":\"critical\"}"},
        # When it HAPPENED (writer-set ISO8601). Distinct from the auto
        # ``created_at`` (when the row was recorded): backfilled events carry the
        # issue's original time, so the timeline reads in true chronological order.
        {"name": "ts", "type": "TEXT", "required": True,
         "description": "ISO8601 time the event happened; the timeline sorts by this"},
    ],
}


def ensure_events_table(pod: Pod) -> bool:
    """Create the ``events`` table if it does not exist. Idempotent.

    Returns True if it created the table, False if it already existed.
    """
    existing = {t.name for t in pod.tables.list().items}
    if TABLE_NAME in existing:
        return False
    pod.tables.create(CreateTableRequest.from_dict(EVENTS_SCHEMA))
    return True
