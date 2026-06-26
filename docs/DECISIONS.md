# Decision Log (ADR-lite)

Three lines per decision: **Decision / Why / Rejected.** This doc feeds the 25% "product judgment —
any wasted complexity?" score and the hiring track's "how they scoped and defended decisions."

---

### D-001 · Lemma is the entire backend
- **Decision:** Use Lemma Tables, Files, Agents, Workflows, Functions, App — no custom backend.
- **Why:** Lemma already provides them; rebuilding is wasted complexity (penalized) and costs SDK-utilisation points (15%).
- **Rejected:** FastAPI + Postgres + custom React. Reason: duplicates the platform we're graded on using.

### D-002 · No vector database
- **Decision:** Duplicate detection via `pod.files.search(search_method="HYBRID")`.
- **Why:** Files are auto-chunked + embedded; hybrid search is built in.
- **Rejected:** Qdrant / Pinecone / Weaviate / Milvus + embeddings pipeline. Reason: redundant, demo scale is ~20 issues not 10M vectors.

### D-003 · No Postgres / Redis of our own
- **Decision:** One `issues` Lemma Table; no cache layer.
- **Why:** Demo-scale data; Tables cover structured storage; no queue load to justify Redis.
- **Rejected:** 7-entity relational schema. Reason: hours of schema work that never appears on camera.

### D-004 · Read-only GitHub via PAT (no OAuth)
- **Decision:** Personal Access Token, read-only.
- **Why:** OAuth app registration + callbacks can eat half a day for zero demo value.
- **Rejected:** Full GitHub OAuth. GitHub is NOT a Lemma Surface, so this is the one connector we build.

### D-005 · Slack/Email via Surfaces or seed (not hand-built webhooks)
- **Decision:** Use Lemma Surfaces if time allows; otherwise seeded JSON into the same Table.
- **Why:** Surfaces include webhook ingress + identity resolution for free.
- **Rejected:** Hand-built FastAPI webhooks per source.

### D-006 · Evidence, not confidence percentages
- **Decision:** Investigation shows clickable evidence links, never a "91%" figure.
- **Why:** LLM-emitted percentages are uncalibrated theater; evidence is verifiable.
- **Rejected:** Confidence % UI from the original draft.

### D-007 · One persona, one hero loop
- **Decision:** Build for "Alex, founding engineer." Hero loop = ingest → triage+dedup → queue → investigate. Release Center is the only optional feature.
- **Why:** 35% problem-fit rewards a specific user; a working narrow loop beats five broken features.
- **Rejected:** Bug graph, analytics dashboard, command palette, multi-repo, CI/Sentry, breaking-change diff analysis.

### D-008 · Pin `lemma-sdk==0.5.0`; build against the introspected API
- **Decision:** Use the real `lemma-sdk` (import root `lemma_sdk`), pinned at 0.5.0; verified every call by introspecting the installed package, not by trusting the PRD's assumed syntax.
- **Why:** The PRD/contract had guessed env-var names (`LEMMA_POD_URL`/`LEMMA_API_KEY`) and a `files.write` that don't exist; building on guesses would fail at the live checkpoint. Ground-truth introspection is cheap insurance for the 15% SDK-utilisation score.
- **Rejected:** Coding against the PRD pseudocode as-is. Reason: wrong env vars, wrong file API, would silently break Day-1 integration.

### D-009 · `github_fetch` as a plain Python connector (not a deployed Lemma Function yet)
- **Decision:** Day 1 `github_fetch` is an importable Python module using `requests`; defer wrapping it as a deployed Lemma Function unless a workflow needs it server-side.
- **Why:** The connector logic is the work; it's testable without a pod and unblocks ingest immediately. GitHub is the one non-Surface source, so this is the only connector we own.
- **Rejected:** Standing up a deployed Lemma Function on Day 1. Reason: deployment overhead with no demo value yet.

### D-010 · Operator UI is a single-file HTML Lemma App (not Vite/React)
- **Decision:** Build `app/index.html` as a no-build HTML Lemma App (loads `lemma-client.js` from the host-injected `__LEMMA_CONFIG__`), with a `DataSource.listIssues()` seam that reads `seed/issues.json` in mock mode and `client.records.list("issues")` against the live pod.
- **Why:** The whole product is one operator console (queue → detail → investigate); HTML deploys with zero build and dodges the Windows/patched-CLI Vite build+deploy risk. The mock/live seam lets Lane B build full-speed against seed data with no dependency on Lane A — exactly the Day-1 parallelism the plan calls for.
- **Rejected:** Vite + React scaffold. Reason: routing/bundler overhead for a single-surface app, plus a heavier deploy path on Windows; revisit only if the UI genuinely needs client-side routing/state later.

### D-011 · D2+ agents/functions are bundle-authored (not SDK-scripted)
- **Decision:** Author the triage agent + `normalize_priority` function (and later the investigate workflow) as a **local pod bundle** (`pod/pod.json` + `pod/agents/*`, `pod/functions/*`) imported with `lemma pods import`, per the `lemma-builder` skill. The agent is a **read-only classifier** (POD toolset, granted `issues:read` + `/issues:read`, `output_schema` = `{priority, repro_steps, reason}`); `normalize_priority` is the validate-and-write step (coerce priority→enum, default `normal`, write back `status:'triaged'`); a Python SDK driver in `ingest/` orchestrates run→normalize→log over untriaged rows.
- **Why:** Agents are pod-resident config (instruction + toolsets + name-based grants), not Python objects — bundles make them versioned, diffable, and re-importable, and the skill is the authoritative guide. Keeping the agent read-only and pushing the write into a granted function keeps the LLM out of the data-integrity path (the 15% SDK-utilisation + 25% product-judgment scores reward this separation). D1's direct-SDK scripts stay for table/ingest plumbing — bundles are additive, not a rewrite.
- **Rejected:** Instantiating/agentic writes from a raw SDK script (no versioned agent resource, no grant boundary), and letting the agent write priorities directly (puts an LLM on the integrity path with no enum validation). The pod shell already exists, so `import` only upserts the new resources.

### D-012 · D3 dedup discovers links; demo dup-partners loaded into the live pod
- **Decision:** Duplicate detection is `find_similar` (Function: HYBRID `files.search` over `/issues`, top-5 excluding self) → `dedup_confirm` (read-only agent, one YES/NO with `{is_duplicate, reason}` per contract §4) → `link_related` (Function: symmetric, idempotent `related_ids` write to both rows), driven by `ingest/dedup/run_dedup.py`. As a prerequisite, `scripts/seed_demo_dups.py` loads the 6 curated GitHub dup-partners (`gh_142/158/171/192/201/209`) from `seed/issues.json` into the live pod (rows + `/issues/*.md` files) and **resets every `related_ids` to `[]`** so dedup discovers links from scratch rather than trusting the fixture's pre-wired pairs.
- **Why:** The live pod was bootstrapped with the *real* `cli/cli` issues, so the seeded Slack/email feedback had no matching GitHub partner to dedup against — dedup could find nothing. The curated partners are exactly the deterministic "genuine duplicates" the plan's seed strategy calls for. Clearing `related_ids` makes the verification honest: dedup must re-derive the known pairs, and the LLM confirm step must reject the one weak/thematic pair (`gh_201`↔`iss_021`, rate-limit-backoff vs debug-headers) to prove precision, not just recall.
- **Rejected:** (a) Running dedup only over the real `cli/cli` issues — they contain no genuine duplicate cluster, so nothing to demo. (b) Trusting the fixture's pre-set `related_ids` — that skips the actual discovery+confirm work being graded. (c) A vector DB — D-002 already settled HYBRID `files.search`.

### D-013 · Investigation is a workflow of fast deterministic gatherers + one synthesis agent
- **Decision:** The `investigate` workflow is `intake (FORM: issue_id)` → three deterministic FUNCTION gatherers (`analyze_stacktrace`, `fetch_related_commits`, `find_similar_evidence`) → one `investigate_synth` AGENT → END. Each gatherer returns **evidence already carrying a real URL** (the report file link, GitHub commit `html_url`s, GitHub issue URLs for github-source matches); the synthesis agent only writes the hypothesis and **selects ≤3** of the provided evidence items — it never invents a URL (D-006). `fetch_related_commits` hits the **public** GitHub commits API (cli/cli is public; PAT optional via config) so no secret lives in the function.
- **Why:** One LLM call (synthesis) keeps the run < ~15s (box 6); the gatherers are deterministic, individually testable, and auditable. Supplying URLs from code rather than the LLM keeps evidence verifiable, not hallucinated — the whole point of "evidence, not confidence %". Splitting gather vs. synthesize matches the workflow node model (functions = reliable verbs, one agent = one cohesive judgment).
- **Rejected:** An AGENT node per gathering step (3–4 LLM calls → slow, >15s, costlier, harder to keep < budget) and letting the synthesis agent fetch/construct URLs itself (fabrication risk + extra tool-call latency). `find_similar_evidence` is a workflow-specific sibling of `find_similar` because function output schemas are immutable after create — adding URL/source fields to the existing `find_similar` would require delete+recreate.

---

## Scope & kill criteria (Phase 0 agreement)
- **Lanes:** Dev A = Lemma Core (pod/agents/workflows/functions/ingest). Dev B = App & Demo (app/seed/recording/writeup).
- **Workflow:** trunk-based on `main`, conventional commits, one commit per checklist box, pull-before-push, folder ownership avoids conflicts.
- **Contract-first:** `docs/contracts.md` is frozen; build both lanes against it in parallel.
- **Kill criteria:**
  - Drop Release Center on **D4 AM** if investigation isn't solid.
  - Switch to **pre-recorded** investigation if live run is flaky by **D5 noon**.
  - Any task >2× its estimate → stop, sync, re-scope.

### Open decisions (TBD)
- Slack/Email: Surfaces vs seed — decide by end of D2.
- Release Center: go/no-go — decide D4 AM (record here).
