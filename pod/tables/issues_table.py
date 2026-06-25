"""The ``issues`` Table — the one structured store for all feedback.

Schema follows ``docs/contracts.md`` §1. The backend auto-materializes the
``id`` primary key, ``created_at`` and ``updated_at`` system columns, so we do
not declare those here (we DO declare ``id`` as a TEXT primary key because Forge
assigns its own human-readable ids like ``gh_142``, rather than letting the
backend mint a UUID).

RLS is disabled: ``issues`` is a shared team table that the App and both devs
read/write, not per-user personal data.
"""

from __future__ import annotations

from lemma_sdk import Pod
from lemma_sdk.openapi_client.models.create_table_request import CreateTableRequest

TABLE_NAME = "issues"

# Enum option sets, kept in sync with docs/contracts.md.
SOURCES = ["github", "slack", "email"]
PRIORITIES = ["critical", "high", "normal", "low"]
STATUSES = ["new", "triaged", "investigating", "resolved"]

# create_from_dict payload. `type` is the wire key for the column data type.
ISSUES_SCHEMA: dict = {
    "name": TABLE_NAME,
    "primary_key_column": "id",
    "enable_rls": False,
    "columns": [
        {"name": "id", "type": "TEXT", "required": True,
         "description": "Forge-internal id, e.g. gh_142 / iss_001"},
        {"name": "source", "type": "ENUM", "options": SOURCES, "required": True},
        {"name": "external_id", "type": "TEXT",
         "description": "GitHub issue number (e.g. 142); null for seeded chat"},
        {"name": "title", "type": "TEXT", "required": True},
        {"name": "body", "type": "TEXT",
         "description": "full report text (also written to Files)"},
        {"name": "priority", "type": "ENUM", "options": PRIORITIES,
         "description": "null until triaged"},
        {"name": "repro_steps", "type": "TEXT",
         "description": "markdown bullet list; null until triaged"},
        {"name": "status", "type": "ENUM", "options": STATUSES,
         "required": True, "default": "new"},
        {"name": "related_ids", "type": "JSON", "default": [],
         "description": "ids of confirmed duplicates / related issues"},
        {"name": "linked_prs", "type": "JSON", "default": [],
         "description": "PR identifiers that fix it (optional)"},
    ],
}


def ensure_issues_table(pod: Pod) -> bool:
    """Create the ``issues`` table if it does not exist. Idempotent.

    Returns True if it created the table, False if it already existed.
    """
    existing = {t.name for t in pod.tables.list().items}
    if TABLE_NAME in existing:
        return False
    pod.tables.create(CreateTableRequest.from_dict(ISSUES_SCHEMA))
    return True
