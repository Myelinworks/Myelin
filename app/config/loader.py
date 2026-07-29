"""Cached loaders for the two config layers.

`parse_float=Decimal` matters: it keeps every coefficient exact from JSON through to arithmetic.
Parsing `0.02` as a float and multiplying by 8.7 does not give 1.174.
"""

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config.schema import CompanySeed, SimulationProfile

PROFILES_DIR = Path(__file__).parent / "profiles"
SEEDS_DIR = Path(__file__).parent / "seeds"


def _read(directory: Path, name: str, kind: str) -> dict[str, Any]:
    path = directory / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in directory.glob("*.json"))
        raise FileNotFoundError(f"No {kind} config named '{name}' (available: {', '.join(available) or 'none'})")
    with path.open(encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


@lru_cache
def load_profile(name: str = "default") -> SimulationProfile:
    """Load a simulation profile -- curve shapes only, no company numbers."""
    return SimulationProfile.model_validate(_read(PROFILES_DIR, name, "profile"))


@lru_cache
def load_seed(name: str) -> CompanySeed:
    """Load a company seed -- opening state only, no curve shapes."""
    return CompanySeed.model_validate(_read(SEEDS_DIR, name, "seed"))
