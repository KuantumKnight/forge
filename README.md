# Forge — AI Bug Triage & Release Operator

Turns messy engineering feedback (GitHub issues, Slack, email) into an organized, prioritized,
de-duplicated issue queue, then investigates the hard ones with an AI workflow that **grounds its
root-cause hypothesis in the actual source** — it reads the real `cli/cli` code, cites the exact
line, and proposes a fix as a diff you can click through and verify. Built entirely on the **Lemma SDK**.

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
Lemma is the whole backend: **Tables** (structured `issues` + an `events` audit trail), **Files**
(auto-embedded, hybrid search = dedup + RAG, no vector DB), **Agents** (triage, dedup-confirm,
investigate-synth), a **Workflow** (`investigate`: analyze → related commits → similar issues →
**ground the symbol in real source** → synthesize), **Functions** (github_fetch, find_similar,
fetch_source_evidence, the override writers set_priority/set_assignee/set_status, …), and an **App**
(operator UI). No Postgres / Redis / Qdrant of our own.

## Trust controls (POST-D5)
A real triage product needs trust, not just throughput:
- **Multi-source switcher** — group the queue by source *and* account (GitHub repo, Slack channel,
  email mailbox) via `issues.source_account`. Multi-repo is real: GitHub ingest stamps the repo.
- **Human override controls** — a three-dot menu on the opened issue (Priority / Assignee / Status),
  backed by granted writer Functions. The AI proposes; the operator decides.
- **Audit / evidence timeline** — every issue carries a trail (`ingested → triaged → linked →
  operator overrides`) with timestamps and before→after detail. More useful than an analytics dashboard.

## The hero — verifiable investigation
Open a crashing bug → **Investigate**. The workflow parses the stack frame, finds the crashing symbol
in the **real** repository (public GitHub tree + raw source — no fabrication; if the symbol isn't
found it says so), and the synthesis agent writes a root-cause hypothesis plus a **proposed fix as a
unified diff anchored to the actual lines**. The app renders a clickable `file:Lstart-Lend` citation
that opens the real `cli/cli` source and the diff beside it. Evidence, not vibes — and you can check it.

## Repo layout
```
pod/        agents/ workflows/ functions/ tables/   # Lemma Core  [Dev A]
app/                                                 # Operator UI [Dev B]
ingest/     github/ seed/ triage/ dedup/ investigate # drivers: fetch + triage + dedup + investigate
seed/                                                # demo fixtures + recorded investigation samples
scripts/    smoke.py + per-stage smokes              # full-loop health check
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

```bash
# 5. Run the rest of the loop (each prints PASS/FAIL):
.venv/Scripts/python.exe ingest/seed/load_feedback.py       # Slack/email feedback -> Table + Files
.venv/Scripts/python.exe ingest/triage/run_triage.py        # AI triage: priority + repro on every issue
.venv/Scripts/python.exe ingest/dedup/run_dedup.py          # find + confirm + link duplicates
.venv/Scripts/python.exe ingest/investigate/run_investigate.py gh_142   # the hero: cited hypothesis + fix
```

### One-command health check
`scripts/smoke.py` runs the whole loop (connection → triage → dedup → investigate) and prints a single
PASS/FAIL — run it before any demo take:

```bash
.venv/Scripts/python.exe scripts/smoke.py            # full loop (incl. ~2–3 min live investigate runs)
.venv/Scripts/python.exe scripts/smoke.py --quick    # skip the slow investigate stage (backup take covers it)
```

## Connect to the live pod (Dev B)

The App / seed lane reads and writes the **same `issues` Table** Dev A's pod owns —
the contract in [`docs/contracts.md`](docs/contracts.md) is the seam, and it is current.

- **App (live):** the operator UI is deployed at **https://forge.apps.lemma.work**
  (single-file HTML Lemma App, pod-authenticated). Redeploy after edits with
  `lemma apps deploy forge ./app/index.html --yes`. Served standalone it falls back
  to `seed/issues.json` (mock mode); on the pod it reads the live `issues` Table.
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
