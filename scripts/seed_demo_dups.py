"""D3 prerequisite — make the curated duplicate pairs present + discoverable.

The live pod was bootstrapped with the *real* cli/cli issues, so the seeded
Slack/email feedback (iss_*) had no matching GitHub partner to dedup against.
This loads the 6 curated GitHub dup-partners from ``seed/issues.json`` into the
pod (rows + ``/issues/{id}.md`` Files) and **resets every issue's related_ids to
[]**, so the dedup engine discovers links from scratch instead of trusting the
fixture's pre-wired pairs (see DECISIONS.md D-012).

    .venv/Scripts/python.exe scripts/seed_demo_dups.py
"""

from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from lemma_sdk import LemmaConflictError  # noqa: E402

from pod.lemma_client import get_pod, load_env  # noqa: E402
from pod.tables.issues_table import TABLE_NAME, ensure_issues_table  # noqa: E402

# The curated GitHub partners whose duplicates already live in the pod as
# Slack/email feedback. Loaded so both sides of each pair are searchable.
PARTNER_IDS = ["gh_142", "gh_158", "gh_171", "gh_192", "gh_201", "gh_209"]

SEED_FILE = REPO_ROOT / "seed" / "issues.json"


def _load_seed() -> dict[str, dict]:
    rows = json.loads(SEED_FILE.read_text(encoding="utf-8"))
    return {r["id"]: r for r in rows}


def _row_for(seed_row: dict) -> dict:
    """Bundle row for upsert — related_ids forced to [] for clean discovery."""
    return {
        "id": seed_row["id"],
        "source": seed_row["source"],
        "external_id": seed_row.get("external_id"),
        "title": seed_row["title"],
        "body": seed_row["body"],
        "priority": seed_row.get("priority"),
        "repro_steps": seed_row.get("repro_steps"),
        "status": seed_row.get("status", "triaged"),
        "related_ids": [],
        "linked_prs": [],
    }


def load_partners(pod, seed: dict[str, dict]) -> int:
    created = updated = 0
    for pid in PARTNER_IDS:
        row = _row_for(seed[pid])
        try:
            pod.records.create(TABLE_NAME, row)
            created += 1
        except LemmaConflictError:
            pod.records.update(TABLE_NAME, pid, {
                "title": row["title"], "body": row["body"],
                "priority": row["priority"], "repro_steps": row["repro_steps"],
                "status": row["status"], "related_ids": [],
            })
            updated += 1
        pod.files.write_text(f"/issues/{pid}.md", f"# {row['title']}\n\n{row['body']}")
    return created + updated


def reset_related_ids(pod) -> int:
    """Clear related_ids on every issue so dedup discovers links from scratch."""
    items = pod.records.list(TABLE_NAME, limit=300).to_dict()["items"]
    cleared = 0
    for it in items:
        if it.get("related_ids"):
            pod.records.update(TABLE_NAME, it["id"], {"related_ids": []})
            cleared += 1
    return cleared


def main() -> int:
    load_env()
    pod = get_pod()
    ensure_issues_table(pod)
    seed = _load_seed()

    n = load_partners(pod, seed)
    cleared = reset_related_ids(pod)
    print(
        f"PASS: loaded {len(PARTNER_IDS)} curated GitHub dup-partners "
        f"({n} upserted + /issues files); cleared related_ids on {cleared} row(s). "
        "Files index asynchronously — give them a few seconds before dedup."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
