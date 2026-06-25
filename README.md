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

## Setup (runbook — expanded on Day 5)
```bash
cp .env.example .env     # then fill in MODEL_API_KEY, GITHUB_PAT, GITHUB_REPO, LEMMA_*
# (Lemma SDK install + pod bootstrap steps to be documented as we build — see docs/EXECUTION.md D1)
```

## Team
Team of 2. Lane ownership: **Dev A** — Lemma Core; **Dev B** — App & Demo. See `docs/EXECUTION.md`.
