#input_type_name: FindSimilarEvidenceInput
#output_type_name: FindSimilarEvidenceResult
#function_name: find_similar_evidence
#config_type_name: FindSimilarEvidenceConfig

"""Similar past issues as investigation evidence (contracts.md §5).

The same HYBRID /issues search find_similar runs, but each match is resolved to
a citable evidence item: a real GitHub issue URL for github-source matches, or a
deep-link to the report file otherwise — so the synthesis agent can link to
prior reports of the same problem without inventing URLs.
"""

from typing import List, Optional

from pydantic import BaseModel
from lemma_sdk import Pod


class FindSimilarEvidenceInput(BaseModel):
    issue_id: str
    limit: int = 3


class FindSimilarEvidenceConfig(BaseModel):
    default_repo: str = "cli/cli"


class IssueEvidence(BaseModel):
    type: str
    label: str
    url: str
    source: str
    score: float


class FindSimilarEvidenceResult(BaseModel):
    issue_id: str
    issue_evidence: List[IssueEvidence]


def _id_from_path(path: str) -> Optional[str]:
    if not path:
        return None
    name = path.rstrip("/").rpartition("/")[2]
    return name[:-3] if name.endswith(".md") else name


def _evidence_url(pod, row: dict, repo: str) -> str:
    """A real link for the match: GitHub issue for github source, else report file."""
    if row.get("source") == "github" and row.get("external_id"):
        return f"https://github.com/{repo}/issues/{row['external_id']}"
    try:
        urls = pod.files.get_url(f"/issues/{row['id']}.md")
        return getattr(urls, "app_url", None) or getattr(urls, "url", "") or ""
    except Exception:
        return ""


async def find_similar_evidence(ctx, data: FindSimilarEvidenceInput) -> FindSimilarEvidenceResult:
    cfg = ctx.config or FindSimilarEvidenceConfig()
    repo = getattr(cfg, "default_repo", "cli/cli")
    pod = Pod.from_env()

    issue = pod.table("issues").get(data.issue_id)
    query = f"{issue.get('title', '')}\n{issue.get('body', '')}".strip()

    hits = pod.files.search(
        query, scope_path="/issues", search_method="HYBRID"
    ).to_dict().get("items", [])

    best: dict[str, float] = {}
    for hit in hits:
        cid = _id_from_path(hit.get("path", ""))
        if not cid or cid == data.issue_id:
            continue
        score = float(hit.get("score", 0.0))
        if cid not in best or score > best[cid]:
            best[cid] = score

    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[: data.limit]

    # Batch the candidate row reads into ONE query instead of N gets — round
    # trips dominate latency, so fewer calls is the main lever we control.
    rows_by_id: dict[str, dict] = {}
    if ranked:
        ids = "', '".join(cid.replace("'", "") for cid, _ in ranked)
        try:
            rows = pod.query(
                f"select id, title, source, external_id from issues where id in ('{ids}')"
            ).to_dict().get("items", [])
            rows_by_id = {r["id"]: r for r in rows}
        except Exception:
            rows_by_id = {}

    evidence: List[IssueEvidence] = []
    for cid, score in ranked:
        row = rows_by_id.get(cid)
        if row is None:
            try:
                row = pod.table("issues").get(cid)
            except Exception:
                continue
        src = row.get("source", "unknown")
        label = f"{row.get('title', cid)[:70]} ({src})"
        evidence.append(IssueEvidence(
            type="issue",
            label=label,
            url=_evidence_url(pod, row, repo),
            source=src,
            score=score,
        ))

    return FindSimilarEvidenceResult(issue_id=data.issue_id, issue_evidence=evidence)
