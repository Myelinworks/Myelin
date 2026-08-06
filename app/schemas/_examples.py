"""Loads OpenAPI example payloads captured from the live HTTP test suite -- never hand-typed.

`tests/routes/test_capture_api_examples.py` plays one full run start-to-finish (register, start a
run, submit every department each quarter, handle the Q3 crisis, submit the Q4 endgame decision,
lock, and hit all four refusal envelopes) and writes each real response body to
`docs/examples/captured_payloads.json`. Every `json_schema_extra={"example": example(...)}` below
reads straight from that file, so a schema's documented example is always a real response the app
actually produced, and re-running the capture test after a schema change regenerates it in place --
there is no separate copy to fall out of sync.
"""

import json
from functools import lru_cache
from pathlib import Path

_EXAMPLES_PATH = Path(__file__).resolve().parents[2] / "docs" / "examples" / "captured_payloads.json"


@lru_cache
def _load_examples() -> dict:
    if not _EXAMPLES_PATH.exists():
        # A fresh checkout before the capture test has ever run. Schemas must still import
        # cleanly with no example rather than fail app startup -- `docs/examples/` is committed
        # in this repo, so this branch is not the normal path.
        return {}
    return json.loads(_EXAMPLES_PATH.read_text())


def example(name: str) -> dict:
    """The captured payload for `name`, or `{}` if it hasn't been captured yet."""
    return _load_examples().get(name, {})
