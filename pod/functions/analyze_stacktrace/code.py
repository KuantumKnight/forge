#input_type_name: AnalyzeStacktraceInput
#output_type_name: AnalyzeStacktraceResult
#function_name: analyze_stacktrace

"""Deterministic stack-trace / error analysis over an issue body.

The synthesis agent does the *reasoning*; this node does the *extraction* — fast,
predictable signals it can build on: the error signature line, search keywords
(commands, code spans, identifiers), the named components, and a clickable link
to the originating report file (the first piece of cited evidence).
"""

import re
from typing import List, Optional

from pydantic import BaseModel
from lemma_sdk import Pod

# Lines that look like an error/crash signature, most specific first.
_ERROR_PATTERNS = [
    r"panic:[^\n]*",
    r"Traceback \(most recent call last\)[^\n]*",
    r"nil pointer dereference[^\n]*",
    r"segmentation fault[^\n]*",
    r"fatal:[^\n]*",
    r"HTTP\s+\d{3}[^\n]*",
    r"\b[A-Za-z_][\w.]*(?:Error|Exception)\b[^\n]*",
    r"\b\d{3}\b\s*(?:Bad credentials|Forbidden|Not Found|Unauthorized)[^\n]*",
]


class AnalyzeStacktraceInput(BaseModel):
    issue_id: str


class Evidence(BaseModel):
    type: str
    label: str
    url: str


class AnalyzeStacktraceResult(BaseModel):
    issue_id: str
    error_signature: str          # the crash/error line, or "" if none found
    has_trace: bool               # a stack trace / panic was detected
    keywords: List[str]           # salient search terms (commands, code spans, ids)
    components: List[str]         # files / dotted identifiers implicated
    report_evidence: Optional[Evidence] = None   # link to the originating report


def _dedup(seq: List[str], limit: int) -> List[str]:
    seen, out = set(), []
    for s in seq:
        s = s.strip()
        key = s.lower()
        if s and key not in seen:
            seen.add(key)
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _extract(text: str):
    signature = ""
    has_trace = False
    for pat in _ERROR_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            signature = m.group(0).strip()[:200]
            has_trace = bool(re.search(r"panic:|Traceback|nil pointer|segmentation", text, re.IGNORECASE))
            break

    commands = re.findall(r"\bgh(?:\s+[a-z][a-z-]+){1,2}", text)
    code_spans = re.findall(r"`([^`]{2,40})`", text)
    dotted = re.findall(r"[A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)+", text)   # determineBaseRepo, auth.session
    files = re.findall(r"[\w./-]+\.(?:go|py|js|ts|rb|rs|java)\b", text)

    keywords = _dedup(commands + code_spans, 8)
    components = _dedup(files + dotted, 6)
    return signature, has_trace, keywords, components


async def analyze_stacktrace(ctx, data: AnalyzeStacktraceInput) -> AnalyzeStacktraceResult:
    pod = Pod.from_env()
    issue = pod.table("issues").get(data.issue_id)
    text = f"{issue.get('title', '')}\n{issue.get('body', '')}"

    signature, has_trace, keywords, components = _extract(text)

    report_evidence = None
    try:
        urls = pod.files.get_url(f"/issues/{data.issue_id}.md")
        link = getattr(urls, "app_url", None) or getattr(urls, "url", None)
        if link:
            report_evidence = Evidence(
                type="file",
                label=f"Original report — {issue.get('title', data.issue_id)[:60]}",
                url=link,
            )
    except Exception:
        pass  # report file may not exist for a bare record; evidence is optional

    return AnalyzeStacktraceResult(
        issue_id=data.issue_id,
        error_signature=signature,
        has_trace=has_trace,
        keywords=keywords,
        components=components,
        report_evidence=report_evidence,
    )
