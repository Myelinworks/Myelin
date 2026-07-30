"""Cached loaders for the two config layers.

`parse_float=Decimal` matters: it keeps every coefficient exact from JSON through to arithmetic.
Parsing `0.02` as a float and multiplying by 8.7 does not give 1.174.
"""

import json
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.config.schema import CompanySeed, Scenario, SimulationProfile

PROFILES_DIR = Path(__file__).parent / "profiles"
SEEDS_DIR = Path(__file__).parent / "seeds"
SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def _read(directory: Path, name: str, kind: str) -> dict[str, Any]:
    path = directory / f"{name}.json"
    if not path.exists():
        available = sorted(p.stem for p in directory.glob("*.json"))
        raise FileNotFoundError(f"No {kind} config named '{name}' (available: {', '.join(available) or 'none'})")
    with path.open(encoding="utf-8") as f:
        return json.load(f, parse_float=Decimal)


DEFAULT_PROFILE = "default"


# The cache lives on the inner functions so a default argument can't split one config across two
# cache entries -- lru_cache keys on the call signature, so load_profile() and
# load_profile("default") would otherwise each parse and validate the same file.
@lru_cache
def _profile(name: str) -> SimulationProfile:
    return SimulationProfile.model_validate(_read(PROFILES_DIR, name, "profile"))


@lru_cache
def _seed(name: str) -> CompanySeed:
    return CompanySeed.model_validate(_read(SEEDS_DIR, name, "seed"))


@lru_cache
def _scenario(name: str) -> Scenario:
    return Scenario.model_validate(_read(SCENARIOS_DIR, name, "scenario"))


def load_profile(name: str = DEFAULT_PROFILE) -> SimulationProfile:
    """Load a simulation profile -- curve shapes only, no company numbers."""
    return _profile(name)


def load_seed(name: str) -> CompanySeed:
    """Load a company seed -- opening state only, no curve shapes."""
    return _seed(name)


def load_scenario(name: str) -> Scenario:
    """Load a scenario -- which seed and profile to run, for how many quarters."""
    return _scenario(name)


@lru_cache
def available_scenario_ids() -> tuple[str, ...]:
    """Every shippable scenario, sorted.

    Sorted and returned as a tuple because the deterministic scenario assignment in
    `services/company_service.py` indexes into this: an unstable order would make the same
    company identifier resolve to a different scenario between processes, breaking replay.
    Dropping a new JSON file into `config/scenarios/` is all it takes to add one.
    """
    return tuple(sorted(path.stem for path in SCENARIOS_DIR.glob("*.json")))
