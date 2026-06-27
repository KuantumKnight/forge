# Security pass — secrets in git history

Pre-submission gate (DoD: *No secrets in git history*). Run the scan before tagging.

## Result — 2026-06-27: **PASS (clean)**

No credentials are present in the working tree or anywhere in git history.

### What was checked
- **`.env` never committed.** `git log --all --full-history -- .env '**/.env'` → no commits.
  `.env` is git-ignored and only ever existed locally.
- **No secret-bearing files tracked** — no `*.env`, `*.key`, `*.pem`, `secret`/`credential`
  files, and `logs/` (raw agent transcripts) is git-ignored, not tracked.
- **History-wide content scan** over every blob in `git rev-list --all` for token
  shapes: GitHub (`ghp_`, `github_pat_`, `gho_/ghs_/ghu_`), Anthropic/OpenAI (`sk-ant-`,
  `sk-…`), AWS (`AKIA…`), Slack (`xox[bpars]-…`), Google (`AIza…`), and JWTs
  (`eyJ….….…`) → **0 hits**.
- **Assignment-style secrets** (`*_TOKEN/_PAT/_KEY/SECRET/PASSWORD = <value>`) across all
  history → only benign matches: the empty `.env.example` placeholders and documentation.
- **Bearer / Authorization headers** with a value in the current tree → none.

### Known benign match
- `scripts/smoke_files.py:22` — `TOKEN = "ZQXJ0RG"` is a rare **marker string** written
  into a throwaway file to verify HYBRID file search round-trips. It is not a credential.

### Hygiene in place
- `.gitignore` covers `.env`, `.env.local`, `*.key`, `*.pem`, `logs/`, `*.log`.
- Credentials are supplied at runtime via env vars / the Lemma CLI session
  (`~/.lemma/config.json`), never in code (see `pod/lemma_client.py`, `.env.example`).
- GitHub ingestion uses public, no-auth endpoints; the PAT is optional and only raises
  the rate limit.

### How to re-run
```bash
PAT='ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|gh[ousr]_[A-Za-z0-9]{30,}|sk-ant-[A-Za-z0-9_-]{20,}|sk-[A-Za-z0-9]{32,}|AKIA[0-9A-Z]{16}|xox[bpars]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_-]{30,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}'
git grep -I -nE "$PAT" $(git rev-list --all)   # expect: no output
git log --all --full-history -- .env '**/.env'  # expect: no commits
```

Nothing to rotate. If a future scan finds a key: rotate it at the provider first, then
purge history (`git filter-repo`) and force-push.
