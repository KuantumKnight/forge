# Data Contracts (FROZEN — change only by mutual agreement + a commit)

This is the seam between the two lanes. **Dev B builds the App against these shapes using mock/seed
data while Dev A builds the real pod.** Neither lane renames a field without updating this file and
telling the other person.

---

## 1. `issues` Table

| Field | Type | Notes |
|---|---|---|
| `id` | string (PK) | Forge-internal id, e.g. `iss_001` |
| `source` | enum | `github` \| `slack` \| `email` |
| `external_id` | string | e.g. GitHub issue number `#142`; null for seeded chat |
| `title` | string | short summary |
| `body` | text | full report text (also written to Files) |
| `priority` | enum \| null | `critical` \| `high` \| `normal` \| `low`; null until triaged |
| `repro_steps` | text (markdown) \| null | bullet list; null until triaged |
| `status` | enum | `new` \| `triaged` \| `investigating` \| `resolved` |
| `related_ids` | string[] | ids of confirmed duplicates / related issues |
| `linked_prs` | string[] | PR identifiers that fix it (optional) |
| `created_at` | ISO datetime | |
| `updated_at` | ISO datetime | |

## 2. Files convention (powers dedup + RAG)

- One file per issue: path `/issues/{id}.md`, content = `# {title}\n\n{body}`.
- Product docs (optional) under `/knowledge/...`.
- Write: `pod.files.write_text(path, content)` (the SDK has `write_text`, not `write`).
- Search: `pod.files.search(query, scope_path="/issues", search_method="HYBRID")`.
- Indexing is **async**: a file is only searchable once it reaches `COMPLETED`
  status, so dedup-on-ingest must tolerate a brief delay (poll/retry).

## 3. Triage agent — output JSON (strict)

```json
{
  "priority": "critical | high | normal | low",
  "repro_steps": "- step one\n- step two",
  "reason": "one short sentence — evidence-based, NO fabricated percentages"
}
```
`normalize_priority` Function validates this → coerces unknown/missing priority to `normal`.

## 4. Duplicate confirmation — agent output

```json
{ "is_duplicate": true, "reason": "same null-pointer in auth/cache.py" }
```

## 5. Investigation Workflow — result shape

```json
{
  "issue_id": "iss_001",
  "hypothesis": "One paragraph: most likely root cause and where.",
  "evidence": [
    { "type": "commit | issue | log | file", "label": "human-readable", "url": "https://..." }
  ]
}
```
UI rule: render evidence as clickable links. **No confidence %** — show evidence, not vibes.

## 6. Release notes (only if Release Center is GO) — result shape

```json
{
  "version": "1.2.0",
  "groups": { "Added": ["..."], "Fixed": ["..."], "Changed": ["..."] },
  "markdown": "## 1.2.0\n\n### Added\n- ..."
}
```

---

### Change log for this contract
- 2026-06-25 — initial freeze (Phase 0).
- 2026-06-26 — SDK reality check (Lane A, D1). Pinned `lemma-sdk==0.5.0`. Real
  facts that differ from earlier assumptions, now reflected above + in
  `.env.example`:
  - Import is `from lemma_sdk import Pod` (not `from lemma import Pod`).
  - Auth env vars are `LEMMA_TOKEN` + `LEMMA_POD_ID` (+ optional `LEMMA_BASE_URL`,
    `LEMMA_ORG_ID`), **not** `LEMMA_POD_URL` / `LEMMA_API_KEY`. A `lemma auth login`
    CLI session in `~/.lemma/config.json` also works.
  - Files use `write_text`; search is async (see §2).
  - Tables are created via `pod.tables.create(...)`; `id`, `created_at`,
    `updated_at` are auto-materialized system columns. `issues` is created with
    `enable_rls=False` (shared team table, not per-user).
  - No field names changed — the `issues`/triage/investigation shapes are intact.
- 2026-06-26 — table created live on pod `forge` and verified end-to-end. Two
  facts learned creating it; **no field renames**, so the seam is unchanged:
  - A custom string `id` PK **is** accepted, so the human-readable ids
    (`gh_142`, `iss_001`) in §1 stand exactly as written — `id` is NOT forced to a UUID.
  - JSON column defaults must be a scalar literal — the API rejects `default: []`.
    So `related_ids` / `linked_prs` have no column default; callers write `[]`
    explicitly on insert (ingest already does). File search can also 500
    transiently while a doc is mid-indexing — poll/retry, don't fail on first error.
