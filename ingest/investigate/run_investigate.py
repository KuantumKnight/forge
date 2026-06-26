"""D4 hero — run the `investigate` workflow end-to-end for one issue.

The single live entry point behind both the app's "Investigate" button and the
EOD-D4 smoke. It drives the workflow the way a client must:

    create_run("investigate") --> submit_form(intake, {issue_id}) --> poll run_get
        --> read execution_context.synthesize  ({hypothesis, evidence[]} per contract §5)

On today's degraded backend `submit_form` itself runs the whole graph synchronously
and overruns the SDK's 30s read timeout (see EXECUTION.md D4 box 6). That is expected:
the run keeps executing server-side, so we swallow the timeout and poll `run_get`
(a cheap read) until the run settles, then lift the synthesis node's output.

    .venv/Scripts/python.exe ingest/investigate/run_investigate.py gh_142
"""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
import time

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from pod.lemma_client import get_pod, load_env  # noqa: E402

try:
    from lemma_sdk.errors import LemmaTimeoutError  # noqa: E402
except Exception:  # pragma: no cover - SDK shape guard
    class LemmaTimeoutError(Exception):
        pass

WORKFLOW_NAME = "investigate"
FORM_NODE = "intake"
SYNTH_NODE = "synthesize"

_TERMINAL = {"COMPLETED", "FAILED", "CANCELLED", "ERROR", "STOPPED"}

# Captured live runs are saved here (gitignored) so a wrong/odd hypothesis can be
# inspected without re-running, and so a backup take always exists on disk.
LOG_DIR = REPO_ROOT / "logs" / "investigate"


def _as_dict(obj) -> dict:
    return obj.to_dict() if hasattr(obj, "to_dict") else obj


def _synth_output(run: dict) -> dict:
    """Lift the synthesis node's {hypothesis, evidence[]} from a finished run.

    The workflow stashes each node's return under execution_context.<node_id>.
    """
    ctx = run.get("execution_context") or {}
    out = ctx.get(SYNTH_NODE) or {}
    return out if isinstance(out, dict) else {}


def _log_run(issue_id: str, result: dict) -> None:
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        (LOG_DIR / f"{issue_id}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except Exception as exc:  # logging must never break the run
        print(f"  [warn] could not write investigate log for {issue_id}: {exc}")


def investigate(pod, issue_id: str, timeout_s: int = 180, poll_s: float = 4.0) -> dict:
    """Run the workflow for one issue; return the contract §5 result + run metadata."""
    started = datetime.datetime.now(datetime.timezone.utc)
    run_id = _as_dict(pod.workflows.create_run(WORKFLOW_NAME))["id"]
    try:
        pod.workflows.submit_form(run_id, node_id=FORM_NODE, inputs={"issue_id": issue_id})
    except LemmaTimeoutError:
        # Expected on a slow backend: submit_form drives the graph synchronously and
        # overruns the read timeout. The run continues server-side; poll below.
        pass

    deadline = time.monotonic() + timeout_s
    run: dict = {}
    while time.monotonic() < deadline:
        try:
            run = _as_dict(pod.workflows.run_get(run_id))
        except LemmaTimeoutError:
            time.sleep(poll_s)
            continue
        if run.get("status") in _TERMINAL:
            break
        time.sleep(poll_s)

    synth = _synth_output(run)
    elapsed = (datetime.datetime.now(datetime.timezone.utc) - started).total_seconds()
    result = {
        "issue_id": issue_id,
        "run_id": run_id,
        "status": run.get("status"),
        "elapsed_s": round(elapsed, 1),
        "hypothesis": synth.get("hypothesis", ""),
        "evidence": synth.get("evidence", []),
    }
    # D5 hero — carry the proposed fix (only present when the symbol was grounded
    # in real source) so the app and backup samples can show the verifiable diff.
    if synth.get("proposed_fix"):
        result["proposed_fix"] = synth["proposed_fix"]
    _log_run(issue_id, result)
    return result


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_investigate.py <issue_id>")
        return 2
    load_env()
    pod = get_pod()
    result = investigate(pod, sys.argv[1])
    print(json.dumps(result, indent=2, ensure_ascii=False))
    ok = result["status"] == "COMPLETED" and result["hypothesis"] and len(result["evidence"]) >= 2
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
