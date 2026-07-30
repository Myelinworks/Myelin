"""Regression target for the raw-conversion composition -- Phase 3.5 item 1.

`docs/00-formula-index.md` states raw conversion as `base + Reps + CRM`, which is exact in Q1 but
understates both Q2 variants in `docs/13-quarter-2-reference.md` §4/§5 by an amount that matches HR's
CX Team `Repeat Purchase Rate` bonus almost exactly. See the CX-in-raw-conversion entry in
`docs/10-implementation-gaps.md` for the derivation. Both variants here chain off Q1's own closing
state (`tests/engines/test_quarter_q1.py`'s `q1` fixture) rather than reconstructing Q2's opening
position by hand, so this doubles as a Q1->Q2 chaining check.
"""

from dataclasses import replace
from decimal import Decimal

import pytest

from app.engines.quarter import compute_quarter
from tests.engines.conftest import close
from tests.engines.test_quarter_q1 import Q1_ALLOCATIONS, q1  # noqa: F401 -- fixture import

# docs/13-quarter-2-reference.md §4: Variant A, Efficiency-Final (Rs 42,73,200).
Q2_EFFICIENCY_ALLOCATIONS = replace(
    Q1_ALLOCATIONS,
    google_ads=Decimal("0.50"),
    meta_ads=Decimal("0.50"),
    social_influencer=Decimal("2.50"),
    content_seo=Decimal("1.50"),
    events_pr=Decimal("0.80"),
    email_marketing=Decimal("1.60"),
    referral=Decimal("2.736"),
    prelaunch_buzz=Decimal("1.364"),
    reps=Decimal("6.458"),
    crm_tools=Decimal("2.00"),
    onboarding=Decimal("2.00"),
    quality_qa=Decimal("4.00"),
    innovation=Decimal("3.00"),
    manufacturing=Decimal("1.024"),
    supplier_qc=Decimal("1.25"),
    logistics=Decimal("1.00"),
    culture_benefits=Decimal("1.50"),
    training_development=Decimal("2.00"),
    cx_team=Decimal("1.50"),
    compliance_legal=Decimal("2.20"),
    financial_planning=Decimal("1.80"),
    audit_prep=Decimal("1.50"),
    warranty_years=2,
)

# docs/13-quarter-2-reference.md §5: Variant B, Growth & Profit (Rs 82,63,600).
# Marketing's channel spends here (12.00/5.00/6.00/2.00/1.00/2.00) are independently confirmed by
# the lead totals in §5's own channel table (2,032+569+817+115+90+117+912 = 4,652, matching the
# doc's stated raw total exactly); the doc's Marketing department subtotal (Rs 29,23,600) does not
# match either that or the doc's own grand total (Rs 82,63,600) and is a source-document typo --
# Rs 31,23,600 is the figure consistent with everything else in the section.
Q2_GROWTH_ALLOCATIONS = replace(
    Q1_ALLOCATIONS,
    google_ads=Decimal("12.00"),
    meta_ads=Decimal("5.00"),
    social_influencer=Decimal("6.00"),
    content_seo=Decimal("2.00"),
    events_pr=Decimal("1.00"),
    email_marketing=Decimal("2.00"),
    referral=Decimal("2.736"),
    prelaunch_buzz=Decimal("0.50"),
    reps=Decimal("14.00"),
    crm_tools=Decimal("3.00"),
    onboarding=Decimal("3.00"),
    quality_qa=Decimal("6.00"),
    innovation=Decimal("4.00"),
    manufacturing=Decimal("8.40"),
    supplier_qc=Decimal("1.50"),
    logistics=Decimal("1.50"),
    culture_benefits=Decimal("1.50"),
    training_development=Decimal("2.00"),
    cx_team=Decimal("1.50"),
    compliance_legal=Decimal("2.00"),
    financial_planning=Decimal("1.80"),
    audit_prep=Decimal("1.20"),
    warranty_years=2,
)


@pytest.fixture(scope="module")
def q2_efficiency(q1, profile, nadi_wear):
    return compute_quarter(q1.closing_state, Q2_EFFICIENCY_ALLOCATIONS, profile, nadi_wear)


@pytest.fixture(scope="module")
def q2_growth(q1, profile, nadi_wear):
    return compute_quarter(q1.closing_state, Q2_GROWTH_ALLOCATIONS, profile, nadi_wear)


class TestRawConversionComposition:
    """`raw = base + Reps + CRM + CX Team + Buzz Q+2 bonus` -- verified component by component so
    a future change to any one line's formula fails here before it fails a rounded doc comparison."""

    def test_q1_raw_is_base_plus_reps_plus_crm_plus_cx(self, q1):
        assert close(q1.raw_conversion_pct, "27.25", tolerance="0.05")

    def test_q2_efficiency_reproduces_the_doc(self, q2_efficiency):
        """docs/13-quarter-2-reference.md §4: 'Raw uncapped conversion (Sales+HR alone) = 28.4%'."""
        assert close(q2_efficiency.raw_conversion_pct, "28.4", tolerance="0.05")
        assert q2_efficiency.ceiling_bound is True

    def test_q2_growth_reproduces_the_doc(self, q2_growth):
        """docs/13-quarter-2-reference.md §5: 'Raw uncapped conversion = 31.2%'."""
        assert close(q2_growth.raw_conversion_pct, "31.2", tolerance="0.05")
        assert q2_growth.ceiling_bound is True

    def test_q2_efficiency_final_conversion_rate(self, q2_efficiency):
        """Ceiling 24.0% + Warranty 3.0% = 27.0%, per §4's worked P&L."""
        assert close(q2_efficiency.conversion_ceiling_pct, "24.0", tolerance="0.1")
        assert close(q2_efficiency.conversion_rate_pct, "27.0", tolerance="0.1")

    def test_q2_growth_final_conversion_rate(self, q2_growth):
        """Ceiling 25.0% + Warranty 3.0% = 28.0%, per §5's worked P&L."""
        assert close(q2_growth.conversion_ceiling_pct, "25.0", tolerance="0.1")
        assert close(q2_growth.conversion_rate_pct, "28.0", tolerance="0.1")


class TestGate2BothBranchesOfTheMinAreExercised:
    """Every other Q1/Q2 fixture keeps the ceiling binding, so `MIN(raw, ceiling)` only ever
    selects `ceiling` in the rest of the suite. This constructs the other branch."""

    def test_ceiling_binds_in_every_other_fixture(self, q1, q2_efficiency, q2_growth):
        assert q1.ceiling_bound is True
        assert q2_efficiency.ceiling_bound is True
        assert q2_growth.ceiling_bound is True

    def test_raw_binds_when_rnd_spend_is_high_and_sales_spend_is_low(self, nadi_wear, profile):
        """High Quality/Innovation spend lifts the ceiling far above a deliberately small raw
        conversion (minimal Reps/CRM/CX), so this time `MIN` must select raw, not ceiling."""
        from app.engines.state import CompanyState

        opening = CompanyState.opening(nadi_wear)
        allocations = replace(
            Q1_ALLOCATIONS,
            reps=Decimal("0.20"),
            crm_tools=Decimal("0.10"),
            cx_team=Decimal("0.10"),
            quality_qa=Decimal("40.00"),
            innovation=Decimal("40.00"),
        )
        result = compute_quarter(opening, allocations, profile, nadi_wear)

        assert result.ceiling_bound is False
        assert result.raw_conversion_pct < result.conversion_ceiling_pct
        assert result.conversion_rate_pct == result.raw_conversion_pct + result.warranty_bonus_pts
