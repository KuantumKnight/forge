#input_type_name: FindSimilarInput
#output_type_name: FindSimilarResult
#function_name: find_similar

"""Similarity search for duplicate detection (docs/contracts.md §2).

HYBRID search over the /issues file corpus, mapping the returned chunk paths
(``/issues/{id}.md``) back to issue ids: drop the issue itself, keep each
candidate's best-scoring chunk, return the top-K. Files index asynchronously,
so a freshly written issue may return few/no hits until indexing COMPLETED —
callers tolerate that (poll/retry).
"""

from typing import List, Optional

from pydantic import BaseModel
from lemma_sdk import Pod


class FindSimilarInput(BaseModel):
    issue_id: str
    top_k: int = 5


class SimilarCandidate(BaseModel):
    id: str
    score: float
    title: Optional[str] = None


class FindSimilarResult(BaseModel):
    issue_id: str
    candidates: List[SimilarCandidate]


def _id_from_path(path: str) -> Optional[str]:
    """'/issues/gh_142.md' -> 'gh_142'."""
    if not path:
        return None
    name = path.rstrip("/").rpartition("/")[2]
    return name[:-3] if name.endswith(".md") else name


async def find_similar(ctx, data: FindSimilarInput) -> FindSimilarResult:
    pod = Pod.from_env()

    issue = pod.table("issues").get(data.issue_id)
    query = f"{issue.get('title', '')}\n{issue.get('body', '')}".strip()

    hits = pod.files.search(
        query, scope_path="/issues", search_method="HYBRID"
    ).to_dict().get("items", [])

    # Keep each candidate issue's best chunk score; never match the issue itself.
    best: dict[str, float] = {}
    for hit in hits:
        cid = _id_from_path(hit.get("path", ""))
        if not cid or cid == data.issue_id:
            continue
        score = float(hit.get("score", 0.0))
        if cid not in best or score > best[cid]:
            best[cid] = score

    ranked = sorted(best.items(), key=lambda kv: kv[1], reverse=True)[: data.top_k]

    candidates: List[SimilarCandidate] = []
    for cid, score in ranked:
        title = None
        try:
            title = pod.table("issues").get(cid).get("title")
        except Exception:
            pass  # candidate row may be gone; the file hit is still informative
        candidates.append(SimilarCandidate(id=cid, score=score, title=title))

    return FindSimilarResult(issue_id=data.issue_id, candidates=candidates)
