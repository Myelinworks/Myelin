"""Total Assets identity -- Phase 3.5 item 2.

`docs/00-formula-index.md` has no valuation formula for Total Assets; the identity below is
reverse-engineered from the balance sheets in `docs/12-quarter-1-reference.md` §11 and
`docs/14-quarter-3-reference.md` §1, both reproduced exactly with no tolerance.
"""

from decimal import Decimal

from app.config.schema import EquipmentDepreciationConfig
from app.engines.quarter import _total_assets_inr
from tests.engines.conftest import close
from tests.engines.test_quarter_q1 import q1  # noqa: F401 -- fixture import


class TestTotalAssetsIdentity:
    """`Total Assets = closing cash + carried inventory value + equipment NBV + product IP + AR`."""

    def test_q1_close(self):
        """docs/12-quarter-1-reference.md §11. Inventory value is 729 units x Rs 3,087/unit."""
        total = _total_assets_inr(
            closing_cash_inr=Decimal("11872163"),
            inventory_value_inr=Decimal("729") * Decimal("3087"),
            equipment_nbv_inr=Decimal("2500000"),
            product_ip_inr=Decimal("800000"),
            accounts_receivable_inr=Decimal("1000000"),
        )
        assert total == Decimal("18422586")

    def test_q3_start(self):
        """docs/14-quarter-3-reference.md §1 -- Equipment NBV has depreciated to Rs 20,00,000 by
        the two quarterly steps since Q1 close. Inventory value (Rs 5,15,921 for 173 units) is
        quoted directly on the balance sheet, not decomposed into units x cost/unit there."""
        total = _total_assets_inr(
            closing_cash_inr=Decimal("14125594"),
            inventory_value_inr=Decimal("515921"),
            equipment_nbv_inr=Decimal("2000000"),
            product_ip_inr=Decimal("800000"),
            accounts_receivable_inr=Decimal("1000000"),
        )
        assert total == Decimal("18441515")


class TestQ1ValuationDerivesAssetsFromTheIdentity:
    """The live chain, not a standalone arithmetic check: `q1` (docs/12 seed + Q1 allocations)
    must reach the same Total Assets identity via the engine.

    The chain carries carried inventory and unit cost unrounded, where §11 uses its own rounded
    729 units x Rs 3,087/unit -- so the live figure (Rs 1,72,23,481) is Rs 895 above §11's Rs
    1,72,22,586, the same category of drift `test_quarter_q1.py::TestQ1Valuation` documents for
    the intangible term (see that test for the full breakdown).
    """

    def test_asset_based_no_longer_gaps(self, q1):
        assert q1.valuation.gap_reason is None
        assert close(q1.valuation.asset_based_inr, "17223481", tolerance="5")

    def test_blended_valuation_uses_the_live_asset_term(self, q1):
        assert q1.valuation.blended_inr is not None
        assert close(q1.valuation.blended_inr, "52507746", tolerance="5")


class TestEquipmentDepreciationIsFlaggedNotAuthoritative:
    """Two data points, no stated rule -- same pattern as the fitted brand multiplier
    (`profile.marketing.brand_multiplier.status == "fitted_not_confirmed"`)."""

    def test_status_flag_is_present(self, nadi_wear):
        depreciation = nadi_wear.equipment_depreciation
        assert isinstance(depreciation, EquipmentDepreciationConfig)
        assert depreciation.status == "inferred_from_two_data_points"
        assert depreciation.per_quarter_inr == Decimal("250000")

    def test_this_quarter_s_valuation_uses_the_undepreciated_opening_balance(self, q1, nadi_wear):
        """Q1's own valuation must use the seeded Rs 25,00,000, not Rs 25,00,000 minus a quarter
        of depreciation -- depreciation only discounts what Q2 inherits, mirroring how the Cash
        Efficiency Bonus discounts next quarter's fixed costs rather than this quarter's own.

        A tolerance of Rs 5 is tight enough to catch the bug: using the depreciated Rs 22,50,000
        instead would move asset_based_inr by the full Rs 2,50,000 depreciation step.
        """
        assert close(q1.valuation.asset_based_inr, "17223481", tolerance="5")

    def test_next_quarter_inherits_the_depreciated_balance(self, q1, nadi_wear):
        expected = nadi_wear.equipment_nbv_inr - nadi_wear.equipment_depreciation.per_quarter_inr
        assert q1.closing_state.equipment_nbv_inr == expected
