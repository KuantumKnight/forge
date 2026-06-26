# Forge — AI Bug Triage & Release Operator

Turns messy engineering feedback (GitHub issues, Slack, email) into an organized, prioritized,
de-duplicated issue queue, investigates the hard ones with an AI workflow that cites real evidence,
and prepares release notes on command. Built entirely on the **Lemma SDK**.

> Gappy AI National Hackathon · Powered by Lemma SDK · Team of 2 · June 24–30, 2026.
> Product name: **Forge**. (Gappy AI is the organizer, not the product.)

## Status
🚧 In active build (June 25–30). See [`docs/EXECUTION.md`](docs/EXECUTION.md) for the live checklist.

## Docs
- [`docs/PRD.md`](docs/PRD.md) — product requirements & scope.
- [`docs/EXECUTION.md`](docs/EXECUTION.md) — day-by-day task checklist, lane split, commits.
- [`docs/contracts.md`](docs/contracts.md) — frozen data contracts (the seam between the two lanes).
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — decision log (scope cuts + rationale).
- [`docs/demo-script.md`](docs/demo-script.md) — 3-minute recording storyboard.

## Architecture (one line)
Lemma is the whole backend: **Tables** (structured issues), **Files** (auto-embedded, hybrid search =
dedup + RAG, no vector DB), **Agents** (triage), **Workflows** (investigate, prepare_release),
**Functions** (github_fetch), and an **App** (operator UI). No Postgres / Redis / Qdrant of our own.

## Repo layout
```
pod/        agents/ workflows/ functions/ tables/   # Lemma Core  [Dev A]
app/                                                 # Operator UI [Dev B]
ingest/     github/                                  # GitHub fetch [A]
seed/                                                # demo fixtures [B]
scripts/    smoke                                    # full-loop health check
docs/                                                # PRD, EXECUTION, contracts, decisions
```

## Setup (runbook)

**Prereqs:** Python 3.11+ and [`uv`](https://docs.astral.sh/uv/). The Lemma SDK requires Python ≥ 3.11.

```bash
# 1. Python deps into a local venv
uv venv --python 3.11 .venv
uv pip install -r requirements.txt

# 2. Lemma CLI (for auth + pod management)
uv tool install lemma-terminal
lemma auth login                 # opens a browser; stores a session in ~/.lemma/config.json
```
> **Windows caveat:** the `lemma` CLI currently crashes on every command with
> `ModuleNotFoundError: No module named 'termios'`. Fix: edit
> `…/uv/tools/lemma-terminal/Lib/site-packages/lemma_cli/cli_core/select.py` and wrap
> `import termios` / `import tty` in `try/except ImportError` (set both to `None`),
> then gate the arrow-selector on `termios is not None`. It falls back to numbered
> selection. Re-apply if the CLI is reinstalled/upgraded.

```bash
# 3. Pod + env. The forge pod already exists (Dev A created it). Point .env at it:
cp .env.example .env
#   set LEMMA_POD_ID=019f01ec-5992-732f-b395-a2b29fc87254   (token comes from the CLI session)
#   set GITHUB_REPO=owner/name                              (e.g. cli/cli) for ingestion
#   GITHUB_PAT / MODEL_API_KEY optional until needed

# 4. Verify the Lane A loop end-to-end (each script prints PASS/FAIL):
.venv/Scripts/python.exe scripts/check_connection.py        # pod connects
.venv/Scripts/python.exe scripts/init_pod.py                # create the issues table (idempotent)
.venv/Scripts/python.exe scripts/smoke_issues.py            # record round-trip
.venv/Scripts/python.exe scripts/smoke_files.py             # file write + HYBRID search
.venv/Scripts/python.exe ingest/github/ingest_issues.py     # real GitHub issues -> Table + Files
```
After step 4 the `issues` Table holds real issues, each with its body at `/issues/{id}.md`.

## Connect to the live pod (Dev B)

The App / seed lane reads and writes the **same `issues` Table** Dev A's pod owns —
the contract in [`docs/contracts.md`](docs/contracts.md) is the seam, and it is current.

- **Pod:** `forge` · id `019f01ec-5992-732f-b395-a2b29fc87254` (org *Knight's Workspace*).
- **Auth:** `lemma auth login` (your own account; ask Dev A to add you to the pod), then
  set `LEMMA_POD_ID` in `.env` as above. Token is read from the CLI session — no key in code.
- **Read it from Python:** `from pod.lemma_client import get_pod` →
  `get_pod().records.list("issues", limit=100)`. Field shapes per `contracts.md §1`
  (note: `id` is the human-readable key like `gh_142`; `related_ids`/`linked_prs` arrive as lists).
- **Until you're added to the pod**, keep building against `seed/issues.json` in the same
  shape — that's exactly why the contract is frozen.

## Team
Team of 2. Lane ownership: **Dev A** — Lemma Core; **Dev B** — App & Demo. See `docs/EXECUTION.md`.
