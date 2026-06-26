# Demo Script — 3-minute screen recording

> Drafted on D3, rehearsed from D3, recorded D6. Runs on the curated `seed/` dataset for determinism.

## Storyboard

| # | Beat | Time | Screen action | Voiceover |
|---|---:|---|---|---|
| 1 | The pain | 0:00-0:15 | Show the seeded GitHub, Slack, and email rows or a quick split view of the fixtures. | "Alex is the founding engineer. Bugs arrive in GitHub, Slack, and support email, and every morning starts with sorting the pile." |
| 2 | Ingest to queue | 0:15-0:45 | Run or show the seed/GitHub ingest result, then open Forge Priority Queue. Critical issues are first. | "Forge writes every report into one Lemma Table, indexes the raw text as Files, and the triage agent ranks the queue. Alex did not sort anything." |
| 3 | Dedup | 0:45-1:05 | Open `gh_142` or `gh_158`; show the `N related` badge and related panel links. | "The duplicate reports are already connected. This crash from GitHub is the same thing support and Slack reported." |
| 4 | Investigation | 1:05-1:55 | Trigger the investigate workflow for the selected issue; show progress, hypothesis, and evidence links. | "Now Forge investigates with evidence: similar reports, issue text, and GitHub context. No fake confidence score, just cited evidence." |
| 5 | Release notes, if built | 1:55-2:15 | Show Release Center or skip cleanly if killed. | "If there is time, the same loop turns fixed issues into release notes. If not, this is deliberately cut." |
| 6 | Lemma point | 2:15-2:45 | Show Lemma pod resources: `issues` Table, `/issues` Files, triage agent, functions, workflow. | "The backend is Lemma: Tables for state, Files for hybrid search, Agents for judgment, Functions for guarded writes, and Workflows for investigation." |
| 7 | Close | 2:45-3:00 | Return to the queue on the critical bug. | "Forge makes the next critical bug and the context to fix it the first thing Alex sees." |

## Demo Anchors

- Open `gh_142` for the nil-pointer crash; it is linked to `iss_003`.
- Open `gh_158` for SSO/token failures; it is linked to `iss_007`.
- Use the source filter to show that GitHub, Slack, and Email all land in the same queue.
- Keep the queue in mock mode if live pod auth is flaky; the row shape is identical.

## Rehearsal Notes

- Keep the first pass under 2:45 so there is room for a stumble.
- Do not mention implementation details that are invisible on screen unless the Lemma pod is visible.
- If investigation is slow by D5 noon, use a recorded run for beat 4 and say it is a captured workflow run.
- Record two backup takes after the D4 investigation checkpoint.
