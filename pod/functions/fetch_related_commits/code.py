#input_type_name: FetchRelatedCommitsInput
#output_type_name: FetchRelatedCommitsResult
#function_name: fetch_related_commits
#config_type_name: FetchRelatedCommitsConfig

"""Related recent commits as investigation evidence (contracts.md §5).

Pulls recent commits from the PUBLIC GitHub commits API and ranks them by how
many of the issue's keywords appear in the commit message — returning the top
few with their real ``html_url`` so the synthesis agent can cite verifiable
links. cli/cli is public, so no token is needed; a PAT may be supplied via
config purely to raise the rate limit (never hard-coded).
"""

import re
from typing import List, Optional

import requests
from pydantic import BaseModel

API_ROOT = "https://api.github.com"


class FetchRelatedCommitsInput(BaseModel):
    keywords: List[str] = []
    repo: Optional[str] = None
    limit: int = 3


class FetchRelatedCommitsConfig(BaseModel):
    default_repo: str = "cli/cli"
    github_token: Optional[str] = None
    scan: int = 12


class CommitEvidence(BaseModel):
    type: str
    label: str
    url: str
    matched: bool
    score: int


class FetchRelatedCommitsResult(BaseModel):
    repo: str
    commit_evidence: List[CommitEvidence]
    any_matched: bool


def _terms(keywords: List[str]) -> List[str]:
    out = set()
    for kw in keywords:
        for tok in re.split(r"[^a-zA-Z0-9]+", kw.lower()):
            if len(tok) >= 3:          # drop noise like "gh", "to"
                out.add(tok)
    return list(out)


async def fetch_related_commits(ctx, data: FetchRelatedCommitsInput) -> FetchRelatedCommitsResult:
    cfg = ctx.config or FetchRelatedCommitsConfig()
    repo = data.repo or cfg.default_repo
    scan = getattr(cfg, "scan", 30)

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "forge-investigate",   # GitHub rejects requests with no UA
    }
    token = getattr(cfg, "github_token", None)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    resp = requests.get(
        f"{API_ROOT}/repos/{repo}/commits",
        headers=headers, params={"per_page": min(scan, 100)}, timeout=15,
    )
    if resp.status_code != 200:
        # Degrade gracefully — investigation continues without commit evidence.
        return FetchRelatedCommitsResult(repo=repo, commit_evidence=[], any_matched=False)

    terms = _terms(data.keywords)
    scored = []
    for c in resp.json():
        msg = (c.get("commit", {}).get("message") or "").strip()
        first_line = msg.splitlines()[0] if msg else c.get("sha", "")[:7]
        haystack = msg.lower()
        score = sum(1 for t in terms if t in haystack)
        scored.append((
            score,
            CommitEvidence(
                type="commit",
                label=first_line[:80],
                url=c.get("html_url", ""),
                matched=score > 0,
                score=score,
            ),
        ))

    # Prefer keyword matches; fall back to most-recent if nothing matched.
    matched = [c for s, c in sorted(scored, key=lambda x: -x[0]) if s > 0]
    chosen = (matched or [c for _, c in scored])[: data.limit]

    return FetchRelatedCommitsResult(
        repo=repo,
        commit_evidence=chosen,
        any_matched=bool(matched),
    )
