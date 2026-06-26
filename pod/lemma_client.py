"""Single source of truth for connecting to the Lemma pod.

Every script and Function goes through ``get_pod()`` so the connection logic
(env loading, auth resolution) lives in exactly one place.

Auth resolution (handled by the SDK's ``Pod.from_env``):
  1. ``LEMMA_TOKEN`` env var, else
  2. a CLI session in ``~/.lemma/config.json`` (written by ``lemma auth login``).
``LEMMA_POD_ID`` selects the pod; ``LEMMA_BASE_URL`` defaults to
https://api.lemma.work.

Long-run token refresh: the SDK captures the access token once at construction and
does not refresh it, so a multi-minute batch/smoke (dedup, investigate) can outlive
the CLI session's short-lived access token and die mid-run with a 401 "Access token
has expired". To avoid that, ``get_pod()`` mints a **fresh** token via
``lemma auth print-token`` (which transparently refreshes using the stored refresh
token) and injects it as ``LEMMA_TOKEN`` before constructing the Pod. This is
best-effort: if ``LEMMA_TOKEN`` is already set, or the CLI isn't available, we leave
auth resolution to the SDK's normal path.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import subprocess

from dotenv import load_dotenv
from lemma_sdk import Pod

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]


def load_env() -> None:
    """Load ``.env`` from the repo root into the process environment (no-op if absent)."""
    load_dotenv(REPO_ROOT / ".env")


def _fresh_cli_token() -> str | None:
    """A freshly-refreshed access token from the CLI session, or None.

    ``lemma auth print-token`` refreshes the access token if it has expired, so this
    keeps long-running drivers authenticated past the access-token TTL.
    """
    lemma = shutil.which("lemma")
    if not lemma:
        return None
    try:
        out = subprocess.run(
            [lemma, "auth", "print-token"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:
        return None
    token = (out.stdout or "").strip()
    return token if out.returncode == 0 and token else None


def get_pod() -> Pod:
    """Return a connected pod, reading credentials from ``.env`` / CLI session.

    Mints a fresh CLI access token first (so long batches don't 401 mid-run) unless
    ``LEMMA_TOKEN`` is already provided. Raises ``LemmaConfigError`` / ``ValueError``
    with an actionable message if no pod id or token can be resolved.
    """
    load_env()
    if not os.environ.get("LEMMA_TOKEN"):
        token = _fresh_cli_token()
        if token:
            os.environ["LEMMA_TOKEN"] = token
    return Pod.from_env()
