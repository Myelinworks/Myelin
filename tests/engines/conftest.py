"""Fixtures for the pure-formula tests. No database, no I/O -- these are arithmetic tests."""

from decimal import Decimal

import pytest

from app.config.loader import load_profile, load_seed


@pytest.fixture(scope="session")
def profile():
    return load_profile()


@pytest.fixture(scope="session")
def nadi_wear():
    return load_seed("nadi_wear")


@pytest.fixture(scope="session")
def pulsewear():
    return load_seed("pulsewear")


def close(actual: Decimal, expected: str | Decimal, tolerance: str = "1") -> bool:
    """Q1 worked values are quoted rounded; the phase tolerance is +/-1 unit or +/-Rs 1."""
    return abs(actual - Decimal(expected)) <= Decimal(tolerance)
