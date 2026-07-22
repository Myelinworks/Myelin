import json
from functools import lru_cache
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).parent


@lru_cache
def load_rules(workspace: str) -> dict[str, Any]:
    """Load a workspace's decision-rule config (curriculum constants, loaded once and cached)."""
    path = RULES_DIR / f"{workspace}_rules.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)
