"""Box 6 — map fetched GitHub issues into the issues Table + write bodies to Files.

Each issue becomes one row (id ``gh_<number>``) and one searchable Markdown file
at ``/issues/gh_<number>.md`` (``# {title}\\n\\n{body}``) per docs/contracts.md §2.
Idempotent: re-running updates existing rows instead of erroring.

    GITHUB_REPO=owner/name .venv/Scripts/python.exe ingest/github/ingest_issues.py
"""

from __future__ import annotations

import os
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from lemma_sdk import LemmaConflictError  # noqa: E402

from ingest.github.github_fetch import fetch_open_issues  # noqa: E402
from pod.lemma_client import get_pod, load_env  # noqa: E402
from pod.tables.issues_table import TABLE_NAME, ensure_issues_table  # noqa: E402


def _row_from_issue(issue: dict) -> dict:
    return {
        "id": f"gh_{issue['external_id']}",
        "source": "github",
        "external_id": issue["external_id"],
        "title": issue["title"],
        "body": issue["body"],
        "status": "new",
        "related_ids": [],
        "linked_prs": [],
    }


def ingest_github_issues(pod, repo: str, token: str | None = None, limit: int = 30) -> dict:
    """Fetch open issues from ``repo`` and upsert them into Tables + Files."""
    ensure_issues_table(pod)
    issues = fetch_open_issues(repo, token, limit)

    created = updated = 0
    for issue in issues:
        row = _row_from_issue(issue)
        rid = row["id"]
        try:
            pod.records.create(TABLE_NAME, row)
            created += 1
        except LemmaConflictError:
            # Row already exists — refresh the mutable fields, keep triage state.
            pod.records.update(
                TABLE_NAME, rid,
                {"title": row["title"], "body": row["body"], "external_id": row["external_id"]},
            )
            updated += 1
        pod.files.write_text(f"/issues/{rid}.md", f"# {row['title']}\n\n{row['body']}")

    return {"fetched": len(issues), "created": created, "updated": updated}


def main() -> int:
    load_env()
    repo = os.environ.get("GITHUB_REPO")
    if not repo:
        print("FAIL: set GITHUB_REPO (owner/name) in .env or the environment.")
        return 1
    pod = get_pod()
    stats = ingest_github_issues(pod, repo, os.environ.get("GITHUB_PAT"))
    print(
        f"PASS: ingested {stats['fetched']} issues from {repo} "
        f"({stats['created']} new, {stats['updated']} updated) "
        f"-> Table '{TABLE_NAME}' + Files /issues/*.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
