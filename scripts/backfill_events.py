"""Backfill — stamp ``source_account`` and synthesize the audit trail.

Two one-time backfills over the existing ``issues`` rows so the App's switcher and
timeline have real content from day one (new rows get these for free: ingestion
stamps ``source_account``; triage/dedup/overrides append events going forward).

1. ``source_account`` — derived from the row's OWN content, never fabricated:
     - github → ``cli/cli`` (the repo these were fetched from)
     - slack  → the channel named in the body (``from #eng-help: …``)
     - email  → the mailbox named in the body (``Forwarded from support@: …``)
   Only fills rows where it is currently empty.

2. ``events`` — for each issue, a synthesized trail with TRUE timestamps (``ts``
   offset from the issue's ``created_at``): ``ingested`` (system), then ``triaged``
   (ai) if a priority is set, then ``linked`` (ai) if it has related reports.
   Idempotent: deletes the issue's prior system/ai events first (operator overrides
   are preserved), then rebuilds. ``investigated`` is NOT synthesized — it is a real
   workflow result the App appends live when you run Investigate.

    .venv/Scripts/python.exe scripts/backfill_events.py [--dry-run]
"""

from __future__ import annotations

import json
import pathlib
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from pod.lemma_client import get_pod, load_env  # noqa: E402

SLACK_CHANNEL = re.compile(r"#\s?([a-z0-9][a-z0-9._-]+)", re.I)
EMAIL_MAILBOX = re.compile(r"from\s+([a-z0-9][a-z0-9._+-]*@)", re.I)


def derive_source_account(row: dict) -> str | None:
    source = row.get("source")
    body = row.get("body") or ""
    if source == "github":
        return "cli/cli"
    if source == "slack":
        m = SLACK_CHANNEL.search(body)
        return ("#" + m.group(1)) if m else "#general"
    if source == "email":
        m = EMAIL_MAILBOX.search(body)
        return m.group(1) if m else "support@"
    return None


def _parse_ts(value: str) -> datetime:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)


def synth_events(row: dict) -> list[dict]:
    """The synthesized (system/ai) trail for one issue, in order, with offset ts."""
    base = _parse_ts(row.get("created_at"))
    src = row.get("source") or "unknown"
    label = {"github": "GitHub", "slack": "Slack", "email": "Email"}.get(src, src.title())
    acct = row.get("source_account") or derive_source_account(row)
    events: list[dict] = []

    if src == "github" and row.get("external_id"):
        ingest_summary = f"GitHub issue #{row['external_id']} ingested from {acct}"
    else:
        ingest_summary = f"{label} report ingested" + (f" from {acct}" if acct else "")
    events.append({"kind": "ingested", "actor": "system", "summary": ingest_summary,
                   "detail": {"source": src, "source_account": acct}, "offset": 0})

    if row.get("priority"):
        events.append({
            "kind": "triaged", "actor": "ai",
            "summary": f"AI triaged as {row['priority'].capitalize()}",
            "detail": {"priority": row["priority"], "reason": row.get("triage_reason")},
            "offset": 60,
        })

    related = row.get("related_ids") or []
    if isinstance(related, list) and related:
        n = len(related)
        events.append({
            "kind": "linked", "actor": "ai",
            "summary": f"Linked {n} related report" + ("s" if n != 1 else ""),
            "detail": {"related_ids": related}, "offset": 120,
        })

    out = []
    for e in events:
        out.append({
            "id": "evt_" + uuid.uuid4().hex,
            "issue_id": row["id"],
            "kind": e["kind"], "actor": e["actor"], "summary": e["summary"],
            "detail": json.dumps(e["detail"]),
            "ts": (base + timedelta(seconds=e["offset"])).isoformat(),
        })
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    load_env()
    pod = get_pod()

    issues = [x.to_dict() for x in (getattr(pod.records.list("issues", limit=200), "items", None) or [])]
    existing_events = [x.to_dict() for x in (getattr(pod.records.list("events", limit=1000), "items", None) or [])]

    # account backfill
    acct_fills = 0
    for row in issues:
        if row.get("source_account"):
            continue
        acct = derive_source_account(row)
        if not acct:
            continue
        acct_fills += 1
        if not dry:
            pod.records.update("issues", row["id"], {"source_account": acct})
        row["source_account"] = acct  # so synth_events sees it

    # rebuild synthesized trail (preserve operator events)
    by_issue: dict[str, list[dict]] = {}
    for ev in existing_events:
        by_issue.setdefault(ev.get("issue_id"), []).append(ev)

    deleted = created = 0
    for row in issues:
        for ev in by_issue.get(row["id"], []):
            if ev.get("actor") in ("system", "ai"):
                deleted += 1
                if not dry:
                    pod.records.delete("events", ev["id"])
        for ev in synth_events(row):
            created += 1
            if not dry:
                pod.records.create("events", ev)

    prefix = "[dry-run] would" if dry else ""
    print(f"PASS: {prefix} stamp source_account on {acct_fills} rows; "
          f"{prefix} delete {deleted} stale system/ai events; "
          f"{prefix} create {created} synthesized events over {len(issues)} issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
