"""Box 4 — Files + hybrid search: write a Markdown file, search it back.

Indexing is asynchronous (a file is only searchable once it reaches COMPLETED),
so we poll the search for a rare token until it appears or we time out.

Run:  .venv/Scripts/python.exe scripts/smoke_files.py
"""

from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from lemma_sdk import LemmaError  # noqa: E402

from pod.lemma_client import get_pod  # noqa: E402

PATH = "/issues/_smoke.md"
TOKEN = "ZQXJ0RG"  # rare token unlikely to appear elsewhere
CONTENT = f"# Smoke test issue\n\nUnique token {TOKEN} confirming hybrid search indexing."
TIMEOUT_S = 60
POLL_S = 3


def main() -> int:
    pod = get_pod()
    try:
        pod.files.write_text(PATH, CONTENT)
        print(f"  wrote {PATH}; waiting for indexing (up to {TIMEOUT_S}s)...")

        deadline = time.time() + TIMEOUT_S
        while time.time() < deadline:
            try:
                resp = pod.files.search(TOKEN, scope_path="/issues", search_method="HYBRID")
            except LemmaError:
                # The search backend can 500 transiently while the doc is still
                # indexing; keep polling until it settles or we time out.
                time.sleep(POLL_S)
                continue
            if any(item.path == PATH for item in resp.items):
                top = next(item for item in resp.items if item.path == PATH)
                print(f"PASS: HYBRID search found {PATH} (score={top.score}).")
                return 0
            time.sleep(POLL_S)

        print(f"FAIL: {PATH} not returned by HYBRID search within {TIMEOUT_S}s.")
        print("  (file may still be indexing — re-run, or check files.get(path).status)")
        return 1
    except Exception as exc:
        print(f"FAIL: file search smoke failed: {exc}")
        return 1
    finally:
        try:
            pod.files.delete(PATH)
            print(f"  cleaned up {PATH}")
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
