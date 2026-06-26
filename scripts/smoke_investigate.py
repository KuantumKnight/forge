"""EOD D4 checkpoint — investigate <id> live -> cited hypothesis with evidence.

Runs the real `investigate` workflow over the demo's two critical bugs and
asserts the result the app's detail view renders (renderHypothesisSummary +
renderEvidenceCards): a non-empty root-cause hypothesis and >=2 clickable
evidence links, each shaped {type, label, url} per contract §5.

A passing run is also the "record a backup take" artifact: the captured result
is written to seed/investigate_samples.json so the app (and the on-camera demo)
can fall back to a real, previously-confirmed investigation if the live backend
is too slow on the day. Pass --refresh-samples to rewrite that file.

Run:  .venv/Scripts/python.exe scripts/smoke_investigate.py
      .venv/Scripts/python.exe scripts/smoke_investigate.py --refresh-samples
"""

from __future__ import annotations

import json
import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from pod.lemma_client import get_pod, load_env  # noqa: E402
from ingest.investigate.run_investigate import investigate  # noqa: E402

# The bugs the demo opens on camera (docs/demo-script.md "Demo Anchors").
ANCHORS = ["gh_142", "gh_158"]
# Anchors whose crashing symbol is grounded in REAL repo source (D5 hero): the
# investigation must return a proposed fix anchored to an actual cli/cli line.
SOURCE_GROUNDED = {"gh_142"}
SAMPLES_PATH = REPO_ROOT / "seed" / "investigate_samples.json"


def _check(result: dict, require_fix: bool = False) -> tuple[bool, list[str]]:
    """Assert one investigation matches what the UI needs. Returns (ok, notes)."""
    notes: list[str] = []
    ok = True

    if result.get("status") != "COMPLETED":
        ok = False
        notes.append(f"status={result.get('status')!r} (want COMPLETED)")
    if not result.get("hypothesis"):
        ok = False
        notes.append("empty hypothesis")

    evidence = result.get("evidence") or []
    if len(evidence) < 2:
        ok = False
        notes.append(f"{len(evidence)} evidence link(s) (want >=2)")
    for ev in evidence:
        has_shape = all(ev.get(k) for k in ("type", "label", "url"))
        clickable = str(ev.get("url", "")).startswith(("http://", "https://"))
        if not (has_shape and clickable):
            ok = False
            notes.append(f"bad evidence {ev.get('type')}: shape={has_shape} clickable={clickable}")

    if require_fix:
        # D5 hero — verifiable investigation: a fix anchored to a REAL source line.
        fix = result.get("proposed_fix") or {}
        url = str(fix.get("url", ""))
        cited = any("github.com/cli/cli/blob/" in str(ev.get("url", "")) for ev in evidence)
        if not fix.get("diff"):
            ok = False
            notes.append("no proposed_fix diff (source not grounded)")
        if "github.com/cli/cli/blob/" not in url or "#L" not in url:
            ok = False
            notes.append(f"proposed_fix url not a real cli/cli line link: {url!r}")
        if not fix.get("file_path"):
            ok = False
            notes.append("proposed_fix missing file_path")
        if not cited:
            ok = False
            notes.append("no evidence card cites a real cli/cli source line")
    return ok, notes


def main() -> int:
    refresh = "--refresh-samples" in sys.argv
    load_env()
    pod = get_pod()

    failed = False
    samples: dict[str, dict] = {}
    for issue_id in ANCHORS:
        require_fix = issue_id in SOURCE_GROUNDED
        result = investigate(pod, issue_id)
        ok, notes = _check(result, require_fix=require_fix)
        # The backend is intermittently degraded (EXECUTION.md D4 box 6): a node can
        # transiently FAIL. Retry once before failing the checkpoint, matching the
        # triage batch's transient-failure retry.
        if not ok and result.get("status") != "COMPLETED":
            print(f"     {issue_id} transient {result.get('status')}; retrying once…")
            result = investigate(pod, issue_id)
            ok, notes = _check(result, require_fix=require_fix)
        failed = failed or not ok
        ev_count = len(result.get("evidence") or [])
        print(
            f"{'PASS' if ok else 'FAIL'} investigate {issue_id}: "
            f"status={result.get('status')} {ev_count} evidence in {result.get('elapsed_s')}s"
            + (f" -- {'; '.join(notes)}" if notes else "")
        )
        if ok:
            print(f"     hypothesis: {result['hypothesis'][:90]}…")
            # Keep the contract §5 payload + the proposed fix (when present) the app
            # renders as the backup take.
            sample = {"hypothesis": result["hypothesis"], "evidence": result["evidence"]}
            if result.get("proposed_fix"):
                sample["proposed_fix"] = result["proposed_fix"]
                print(f"     proposed fix: {result['proposed_fix'].get('file_path')} "
                      f"L{result['proposed_fix'].get('line_start')}")
            samples[issue_id] = sample

    if refresh and samples:
        SAMPLES_PATH.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"     wrote backup take -> {SAMPLES_PATH.relative_to(REPO_ROOT)} ({len(samples)} issue(s))")

    print("INVESTIGATE SMOKE PASS" if not failed else "INVESTIGATE SMOKE FAIL")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
