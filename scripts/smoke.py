"""Full-loop smoke — the single "does the core loop work" entry point.

Runs the per-stage smokes in dependency order and prints ONE PASS/FAIL, so it can
be run before every demo take and before submission (EXECUTION.md Part 1 §6). Each
stage is an existing, self-contained smoke; this just sequences them and aggregates.

Stages (the product loop, end to end):
  1. connection      — authenticated pod call works               (check_connection)
  2. triage          — every issue has a valid priority + repro    (smoke_triage)
  3. dedup           — known duplicate pairs are linked            (smoke_dedup)
  4. dedup-in-app    — the live data behind the "N related" view   (smoke_app_dedup)
  5. investigate     — cited root-cause hypothesis + proposed fix  (smoke_investigate)

The investigate stage drives two live workflow runs (~2–3 min each on the degraded
backend), so it is the slow one. Use --quick to skip it for a fast pre-demo check
(a recorded backup take already covers the slow-live case), or --only to run a
subset.

    .venv/Scripts/python.exe scripts/smoke.py            # full loop
    .venv/Scripts/python.exe scripts/smoke.py --quick    # skip the slow investigate run
    .venv/Scripts/python.exe scripts/smoke.py --only connection triage
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import time

SCRIPTS = pathlib.Path(__file__).resolve().parent

# (stage key, script filename, slow?) — order matters: each builds on the last.
STAGES = [
    ("connection", "check_connection.py", False),
    ("triage", "smoke_triage.py", False),
    ("dedup", "smoke_dedup.py", False),
    ("dedup-in-app", "smoke_app_dedup.py", False),
    ("investigate", "smoke_investigate.py", True),
]


def run_stage(key: str, script: str) -> tuple[bool, float]:
    """Run one stage smoke as a subprocess; stream its output; return (ok, secs)."""
    print(f"\n{'=' * 64}\n>> {key}  ({script})\n{'=' * 64}", flush=True)
    started = time.monotonic()
    proc = subprocess.run([sys.executable, str(SCRIPTS / script)])
    elapsed = time.monotonic() - started
    ok = proc.returncode == 0
    print(f"-- {key}: {'PASS' if ok else 'FAIL'} in {elapsed:.0f}s", flush=True)
    return ok, elapsed


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--quick", action="store_true",
                   help="Skip the slow stages (live investigate runs).")
    p.add_argument("--only", nargs="+", metavar="STAGE",
                   help="Run only these stage keys (e.g. --only connection triage).")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    keys = {k for k, _, _ in STAGES}
    if args.only:
        unknown = set(args.only) - keys
        if unknown:
            print(f"unknown stage(s): {', '.join(sorted(unknown))}; valid: {', '.join(sorted(keys))}")
            return 2

    selected = [
        (k, s) for k, s, slow in STAGES
        if (not args.only or k in args.only) and not (args.quick and slow)
    ]
    print(f"Forge full-loop smoke -- {len(selected)} stage(s): "
          f"{', '.join(k for k, _ in selected)}")

    results: list[tuple[str, bool, float]] = []
    for key, script in selected:
        ok, secs = run_stage(key, script)
        results.append((key, ok, secs))

    print(f"\n{'=' * 64}\nSUMMARY\n{'=' * 64}")
    for key, ok, secs in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {key:<14} {secs:>5.0f}s")
    failed = [k for k, ok, _ in results if not ok]
    total = sum(secs for _, _, secs in results)
    if failed:
        print(f"\nFULL-LOOP SMOKE FAIL -- {len(failed)} stage(s): {', '.join(failed)} ({total:.0f}s)")
        return 1
    print(f"\nFULL-LOOP SMOKE PASS -- {len(results)} stage(s) in {total:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
