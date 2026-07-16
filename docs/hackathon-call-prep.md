# Forge Hackathon Top-25 Demo Call Prep

> Call goal: convince the judges that Forge is a focused, working product with strong problem fit, sharp product judgment, real execution, and meaningful Lemma SDK usage.
>
> Format from organizer email: 20-minute Google Meet, covering 2 minutes of problem statement, an end-to-end demo of what you built, and the last 2 minutes on who did what.

---

## 1. The One-Liner Everyone Must Memorize

Forge is an AI bug triage and investigation cockpit for a founding engineer who wakes up to bug reports scattered across GitHub, Slack, and support email.

It makes the next critical bug, duplicate context, source evidence, and first fix direction the first thing Alex sees.

---

## 2. The Winning Angle

Do not pitch Forge as "an AI dashboard" or "a bug tracker." Pitch it as a working operator loop:

```text
Messy feedback -> AI triage -> semantic dedup -> ranked queue -> source-grounded investigation -> inspectable proposed diff
```

The strongest proof point is:

> Forge reads a real issue, links related reports, finds real source lines in `cli/cli`, and proposes a small diff anchored to those fetched lines.

That is the "oh, this is real" moment. Build the call around it.

---

## 3. Team Roles For The Call

Use three clear voices. Do not let everyone improvise over each other.

| Person | Role on call | Owns | Must be ready to answer |
|---|---|---|---|
| Teammate 1 | Product lead / narrator | Problem statement, user pain, why this matters, final close | "Who is this for?", "Why this problem?", "Why not just Jira/Linear/Sentry?" |
| Teammate 2 | Demo driver | Screen share, click path, keeping demo on time | "Can you show that?", "What happens if the workflow is slow?", "Where is the evidence?" |
| Teammate 3 | Technical lead / Q&A | Lemma architecture, agents, workflows, functions, files, tradeoffs | "How is Lemma used?", "What did you cut?", "What is real vs seeded?" |

If one person is strongest at demo driving, that person should share screen and only speak during transitions. The product lead and technical lead can narrate while the driver clicks.

---

## 4. Call Timing Plan

| Time | Segment | Owner | Goal |
|---:|---|---|---|
| 0:00-0:30 | Setup | Product lead | Thank them, confirm screen visible, state structure. |
| 0:30-2:30 | Problem statement | Product lead | Land the pain and user. |
| 2:30-15:30 | End-to-end product demo | Demo driver + Product/Tech narration | Show the full working loop. |
| 15:30-17:30 | Architecture and product judgment | Technical lead | Show Lemma is the stack and explain cuts. |
| 17:30-19:30 | Who did what | All 3 | Crisp contribution split. |
| 19:30-20:00 | Close | Product lead | Repeat the product promise and invite questions if time remains. |

If judges interrupt with questions, answer directly, then return to the flow. The demo driver should keep a private timer visible.

---

## 5. Two-Minute Problem Statement Script

Use this almost verbatim.

> Forge is built for Alex, a founding engineer or dev lead at a 5-15 person startup. Alex does not have a dedicated triage team. Every morning, bug reports arrive from GitHub, Slack, and support email.
>
> The expensive part is not just fixing code. It is deciding what matters first, noticing that three reports are the same underlying crash, finding reproduction steps, and gathering enough source evidence to start the fix.
>
> Existing tools solve pieces of this. GitHub tracks issues. Slack has reports. Support inboxes hold customer pain. Sentry catches runtime errors. But Alex still has to connect those signals manually.
>
> Forge turns that messy stream into one ranked operator queue, then investigates the hard bugs with evidence. It shows the AI's triage reason, related reports, source citations, and a proposed diff that is anchored to real fetched source lines.
>
> The product promise is simple: make the next critical bug and the context to fix it the first thing Alex sees.

Do not mention broad market sizing unless asked. In the call, specificity beats generic scale.

---

## 6. Primary Demo Path

Open before the call:

- Forge app: `https://forge.apps.lemma.work`
- README architecture diagram in another tab, or the Lemma pod resources page if stable.
- Optional terminal ready in repo root for smoke command proof.

Primary demo issue:

- `gh_142`: `gh pr create` nil-pointer crash.
- Related report: `iss_003` Slack report.
- Hero proof: source-grounded investigation, clickable `cli/cli` source line, proposed diff.

Backup demo issue:

- `gh_158`: SSO/token failure.
- Related reports: `iss_007` email report and `iss_025` Slack report with divergent wording.
- Good for proving semantic dedup, because the Slack language is not just keyword-matched.

### Demo Script

1. Show the queue.
   - "This is the operator cockpit. GitHub issues, Slack reports, and support emails land in one queue."
   - Point to source tabs, account switcher, priority chips, status, assignee, and related counts.

2. Filter/switch sources briefly.
   - "The reports keep their source and account context, but they are ranked together."
   - Show GitHub, Slack, Email tabs if fast. Do not linger.

3. Open `gh_142`.
   - "This is a critical GitHub report. The center view shows identity, priority, status, assignee, AI triage reason, original report, and reproduction steps."

4. Show triage reason and reproduction steps.
   - "The triage agent returns strict JSON: priority, repro steps, and reason. A validator writes that result back, so the agent is judging, not directly mutating state."

5. Show related reports.
   - "Dedup uses Lemma Files HYBRID search over Markdown issue files. A read-only dedup agent confirms whether candidates are the same underlying issue, then `link_related` writes symmetric links."
   - Click `iss_003` only if navigation is smooth. Otherwise point and move on.

6. Open the three-dot override menu.
   - "The AI proposes; the operator stays in control. Priority, assignee, and status changes go through granted Lemma Functions."
   - Prefer not to mutate live data unless already rehearsed. Showing the menu is enough.

7. Show audit timeline.
   - "Every important action becomes an event: ingested, triaged, linked, investigated, and operator overrides."

8. Click or show investigation.
   - "Now we run the hero workflow: analyze stack trace, find related commits, find similar issues, ground source evidence, and synthesize."
   - If live workflow is slow, immediately use the saved/captured result and say the fallback line in section 9.

9. Show hypothesis.
   - "The output is evidence-first. We deliberately avoid fake confidence percentages."

10. Show evidence cards.
    - "The synthesis agent can only cite evidence provided by deterministic gatherers."

11. Show proposed fix card.
    - "Because Forge found real `cli/cli` source lines, it renders a small unified diff anchored to those fetched lines. This is not auto-merged. It is an inspectable starting point."

12. Click the source citation if stable.
    - "This is the falsifiable part. The judge can click through to the real file and line."

13. Switch to architecture diagram or pod resources.
    - "The backend is Lemma: Tables for state, Files for hybrid search, Agents for triage and synthesis, Functions for guarded writes and evidence gathering, a Workflow for investigation, and the App for the cockpit."

14. Close the demo.
    - "That is the loop: the next critical bug, duplicate context, source evidence, and first fix direction are first."

---

## 7. What To Say About Lemma SDK Usage

Make this impossible to miss. The judging rubric has SDK usage as a separate score.

| Lemma primitive | Forge usage | Talking point |
|---|---|---|
| Tables | `issues` and `events` | Structured queue state and audit timeline. |
| Files | `/issues/*.md` | HYBRID search for dedup and retrieval, no vector DB. |
| Agents | `triage`, `dedup_confirm`, `investigate_synth` | Judgment steps with constrained output. |
| Functions | `normalize_priority`, `find_similar`, `link_related`, `fetch_source_evidence`, `set_priority`, `set_assignee`, `set_status` | Guarded writes and deterministic evidence gathering. |
| Workflow | `investigate` | Multi-step bug investigation graph. |
| App | `app/index.html` | Single operator cockpit deployed as a Lemma App. |

Short version:

> Lemma is not a thin wrapper in Forge. It is the backend. We used Tables for state, Files for search, Agents for judgment, Functions for trusted actions, a Workflow for investigation, and the App layer for the UI.

---

## 8. Product Judgment: What We Cut And Why

This is a strength. Say it confidently.

| Cut | Why it helps the product |
|---|---|
| Own vector DB | Lemma Files already chunk, embed, and HYBRID-search issue text. |
| Postgres / Redis / FastAPI | Lemma Tables, Functions, Workflows, and App cover the backend for this loop. |
| Fake confidence scores | Evidence links and real source citations are more trustworthy. |
| Release Center | Verifiable investigation was the strongest product moment; depth beat breadth. |
| Live Slack/email OAuth | Auth setup is a demo risk; seeded Slack/email proves the product loop deterministically. |
| Auto-merge fix | Too risky; Forge proposes an inspectable starting diff. |
| Broad analytics dashboard | Alex needs the next fix and evidence trail, not generic charts. |

Best phrasing:

> We cut anything that either Lemma already provides or that would not strengthen the 20-minute demo. The final build is narrow on purpose: one loop, working end to end, with evidence.

---

## 9. Fallback Lines For Demo Risk

### If Live Investigation Is Slow

> The live workflow can take longer depending on backend latency, so for the call I am showing the captured result from the same investigation workflow. The path is the same: stack-trace analysis, related commits, similar reports, source grounding, then synthesis. We keep this fallback because the call is time-boxed, but the artifact still follows the real workflow output contract.

### If The App Shows Seed/Sample Mode

> This mode uses the same issue shape and same UI path. We use it as a deterministic demo fallback. The live pod path has already been smoke-tested; seed mode prevents auth or network latency from wasting the judging window.

### If Asked "Is Slack/Email Live?"

> GitHub is the live read-only source. Slack and email are seeded into the same `issues` Table for a deterministic demo. We intentionally did not spend hackathon time on OAuth setup because the product loop being judged is triage, dedup, investigation, and evidence.

### If Asked "Does It Actually Fix The Bug?"

> It does not auto-merge a fix, and that is deliberate. Forge proposes a small diff anchored to real fetched source lines. A developer can inspect it, copy it, and turn it into a PR. The trust boundary is evidence and review, not blind automation.

---

## 10. Who Did What: Last Two Minutes

Keep this crisp. Each person gets 25-30 seconds, then one team close.

### Teammate 1: Product / Scope / Demo

> I owned the product framing, primary persona, demo story, and scope decisions. I kept the product centered on Alex's triage pain and helped cut features that would weaken the core loop, like broad analytics and release notes.

### Teammate 2: App / UX / Demo Data

> I owned the Lemma App cockpit: ranked queue, source/account switcher, issue detail, related reports, investigation view, proposed diff rendering, human override controls, and audit timeline. I also curated deterministic demo data so the call can be stable.

### Teammate 3: Lemma Backend / Agents / Workflows

> I owned the Lemma pod resources: Tables, Files, triage and dedup agents, validated Functions, the investigation Workflow, source grounding, and smoke scripts. I made sure AI outputs went through guardrails and evidence was generated by deterministic gatherers.

### Team Close

> The team split was contract-first: one data shape, one core loop, then parallel work. That is why the final build is cohesive instead of three disconnected hackathon features.

Adjust names and exact ownership before the call. Do not overstate. If one person did more, still describe the split honestly.

---

## 11. Likely Judge Questions And Strong Answers

### "What problem are you solving?"

We are solving the triage tax for small engineering teams. Bug reports arrive across GitHub, Slack, and support email. Forge ranks them, links duplicates, and gives source-grounded evidence so the engineer starts with context instead of a pile.

### "Who is the user?"

Alex, a founding engineer or dev lead at a 5-15 person startup. The key constraint is that Alex does not have a dedicated triage team.

### "What is the most impressive technical part?"

The investigation workflow. It combines deterministic Functions with one synthesis Agent, grounds a suspected symbol in real `cli/cli` source, and produces evidence plus a proposed diff anchored to fetched lines.

### "How do you prevent hallucinations?"

We separate judgment from writes. Triage returns strict JSON, then a validator writes the enum. Investigation gatherers produce evidence with URLs, and the synthesis agent is instructed to cite only provided evidence. If no source line is found, Forge does not fabricate a proposed fix.

### "Why not use a vector database?"

Lemma Files already provide chunking, embeddings, and HYBRID search. Adding Qdrant or Pinecone would duplicate the platform and weaken the SDK usage story.

### "What is real and what is seeded?"

GitHub issue/source grounding is real against public `cli/cli`. Slack and email reports are seeded into the same Table to make the demo deterministic. The dedup, triage, investigation contract, UI, and event trail run through the actual Forge product path.

### "How is this different from Jira, Linear, GitHub Issues, or Sentry?"

Those tools hold important pieces of the workflow. Forge's wedge is connecting triage, cross-source duplicate detection, and source-grounded investigation in one operator loop for a small team. It is not replacing every tracker; it is making the first fix decision faster and better evidenced.

### "Why did you skip Release Center?"

We initially considered it, then cut it because the strongest product moment was verifiable investigation. Reading real source and proposing a real diff is more defensible than adding a second feature area.

### "What would you build next?"

First: live Slack/Gmail surfaces. Second: PR creation from the proposed diff with human approval. Third: team-specific learning over resolved issues. We would keep the same rule: evidence and guarded writes before automation.

### "What happens when the AI is wrong?"

The operator stays in control. The app shows the reason and evidence, exposes priority/assignee/status overrides, and logs changes in the `events` timeline. Wrong AI output should be inspectable and correctable, not hidden.

### "Can this scale beyond one repo?"

The data model already has `source_account`, and the UI can switch by repo/channel/mailbox. Live multi-repo ingestion is an extension of the GitHub connector, not a new product shape.

---

## 12. Do Not Say These Things

- Do not call the product "Gappy." Gappy AI is the organizer. The product is Forge.
- Do not claim Slack/email OAuth is live unless it actually is.
- Do not say the proposed diff is automatically merged.
- Do not say "91% confidence" or any fake precision.
- Do not pitch Release Center as built in the final product.
- Do not say "fully autonomous engineer." Say "operator cockpit" and "human-in-control."
- Do not over-index on the UI polish. The scoring argument is product loop and proof.

---

## 13. Pre-Call Checklist

Do this at least 45 minutes before the call.

- [ ] All three teammates join a prep Meet and do one full timed run.
- [ ] Confirm who shares screen.
- [ ] Confirm primary demo issue: `gh_142`.
- [ ] Confirm backup demo issue: `gh_158`.
- [ ] Open Forge app: `https://forge.apps.lemma.work`.
- [ ] Open README architecture diagram or Lemma pod resources in second tab.
- [ ] Open this prep doc in another tab.
- [ ] Close unrelated tabs and notifications.
- [ ] Set browser zoom so text is readable on Meet, usually 90-110%.
- [ ] Test microphone for every teammate.
- [ ] Test screen share with audio off.
- [ ] Keep charger plugged in.
- [ ] Keep a phone hotspot ready.
- [ ] Run quick smoke if environment is available:

```powershell
.venv/Scripts/python.exe scripts/smoke.py --quick
```

- [ ] If full live investigation is needed and time allows:

```powershell
.venv/Scripts/python.exe ingest/investigate/run_investigate.py gh_142
```

If smoke fails because of auth or backend latency, do not panic on the call. Use the captured/sample investigation path and be transparent.

---

## 14. Screen Share Setup

Recommended browser tabs:

1. Forge app.
2. README architecture diagram or Lemma pod resources.
3. Optional GitHub source citation tab, if already opened.
4. This prep doc, hidden unless needed.

Recommended screen state:

- Start on Forge queue.
- `gh_142` visible near the top.
- Browser bookmarks hidden.
- Desktop notifications off.
- Terminal minimized unless specifically showing smoke output.

Do not start by showing code. Start by showing the product.

---

## 15. The 30-Second Close

Use this if they give you a final word.

> Forge is intentionally narrow. We did not build another generic dashboard. We built one end-to-end loop: messy reports become a ranked queue, duplicates are linked across sources, the hard bug is investigated with evidence, and the developer gets a source-grounded starting diff. The reason we think this deserves to move forward is that the core workflow is real, inspectable, and built deeply on Lemma rather than around it.

---

## 16. One-Page Cheat Sheet

Memorize these.

**Product:** Forge.

**User:** Alex, founding engineer / dev lead at a 5-15 person startup.

**Pain:** Bug reports scattered across GitHub, Slack, support email; triage tax wastes the morning.

**Promise:** Next critical bug + context to fix it is first.

**Hero:** Source-grounded investigation with clickable real source line and proposed diff.

**Primary issue:** `gh_142`.

**Backup issue:** `gh_158`.

**SDK story:** Tables, Files, Agents, Functions, Workflow, App.

**Best product judgment line:** We cut anything Lemma already provided or that did not make the core loop more convincing.

**Most important honesty line:** Slack/email are seeded for deterministic demo; GitHub/source grounding is real.

**Do not say:** Autonomously merged fix, fake confidence, live Slack OAuth, Release Center built.

