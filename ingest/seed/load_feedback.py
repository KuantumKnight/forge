"""Load seeded Slack/email feedback into the ``issues`` Table.

The loader keeps the same contract as GitHub ingest:
  - rows land in the shared ``issues`` Table
  - each issue body is written to ``/issues/{id}.md`` for Files search
  - re-running is idempotent

Usage:
    python ingest/seed/load_feedback.py --dry-run
    python ingest/seed/load_feedback.py
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Iterable

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_FIXTURES = [REPO_ROOT / "seed" / "slack.json", REPO_ROOT / "seed" / "email.json"]
OPTIONAL_FIELDS = {"external_id", "priority", "repro_steps", "created_at", "updated_at"}
REQUIRED_FIELDS = {"id", "source", "title", "body", "status", "related_ids", "linked_prs"}
SOURCES = {"github", "slack", "email"}
STATUSES = {"new", "triaged", "investigating", "resolved"}
TABLE_NAME = "issues"


def load_fixture(path: pathlib.Path) -> list[dict]:
    """Read and validate one fixture file."""
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"{path} must contain a JSON array")
    for row in rows:
        validate_row(path, row)
    return rows


def validate_row(path: pathlib.Path, row: dict) -> None:
    """Validate the frozen ``issues`` shape enough to fail fast locally."""
    missing = sorted(REQUIRED_FIELDS - row.keys())
    if missing:
        raise ValueError(f"{path}: {row.get('id', '<missing id>')} missing {missing}")
    if row["source"] not in SOURCES or row["source"] == "github":
        raise ValueError(f"{path}: {row['id']} source must be slack or email")
    if row["status"] not in STATUSES:
        raise ValueError(f"{path}: {row['id']} has invalid status {row['status']!r}")
    for field in ("related_ids", "linked_prs"):
        if not isinstance(row[field], list):
            raise ValueError(f"{path}: {row['id']} field {field} must be a list")


def iter_rows(paths: Iterable[pathlib.Path]) -> list[dict]:
    """Return all fixture rows in deterministic file order."""
    rows: list[dict] = []
    seen: set[str] = set()
    for path in paths:
        for row in load_fixture(path):
            if row["id"] in seen:
                raise ValueError(f"duplicate seed id {row['id']}")
            seen.add(row["id"])
            rows.append(row)
    return rows


def row_for_write(row: dict) -> dict:
    """Keep only fields owned by the contract writer path."""
    allowed = REQUIRED_FIELDS | OPTIONAL_FIELDS
    return {key: value for key, value in row.items() if key in allowed}


def write_seed_feedback(pod, rows: Iterable[dict]) -> dict:
    """Upsert seed rows into Tables + Files."""
    from lemma_sdk import LemmaConflictError
    from pod.tables.issues_table import ensure_issues_table

    ensure_issues_table(pod)
    created = updated = 0
    for row in rows:
        payload = row_for_write(row)
        rid = payload["id"]
        try:
            pod.records.create(TABLE_NAME, payload)
            created += 1
        except LemmaConflictError:
            pod.records.update(TABLE_NAME, rid, payload)
            updated += 1
        pod.files.write_text(f"/issues/{rid}.md", f"# {payload['title']}\n\n{payload['body']}")
    return {"created": created, "updated": updated}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        action="append",
        type=pathlib.Path,
        dest="fixtures",
        help="Fixture path to load. Defaults to seed/slack.json and seed/email.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate fixtures and print row count without writing to Lemma.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    fixtures = args.fixtures or DEFAULT_FIXTURES
    rows = iter_rows(fixtures)
    if args.dry_run:
        print(f"PASS: validated {len(rows)} seed feedback rows")
        return 0

    from pod.lemma_client import get_pod, load_env

    load_env()
    stats = write_seed_feedback(get_pod(), rows)
    print(
        f"PASS: loaded {len(rows)} seed feedback rows into '{TABLE_NAME}' "
        f"({stats['created']} new, {stats['updated']} updated) + Files /issues/*.md"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
