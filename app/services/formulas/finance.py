"""Finance workspace engine formulas, taken verbatim from finance_rules.json's engine_formulas.

Division-by-zero guards return 0.0 (or inf for runway with no burn) rather than raising --
these are real states a company can be in (e.g. zero burn before any costs are recorded).
"""


def available_budget(opening_cash: float, reserve_cash: float) -> float:
    return opening_cash - reserve_cash


def closing_cash(opening_cash: float, revenue: float, total_expenses: float, investments: float) -> float:
    return opening_cash + revenue - total_expenses - investments


def monthly_burn(fixed_costs: float, variable_costs: float) -> float:
    return fixed_costs + variable_costs


def quarterly_burn(monthly_burn_value: float) -> float:
    return monthly_burn_value * 3


def cash_runway(cash_available: float, monthly_burn_value: float) -> float:
    if monthly_burn_value == 0:
        return float("inf")
    return cash_available / monthly_burn_value


def debt_ratio(outstanding_debt: float, total_assets: float) -> float:
    return outstanding_debt / total_assets if total_assets else 0.0


def budget_utilisation(total_budget_used: float, total_budget_allocated: float) -> float:
    return total_budget_used / total_budget_allocated if total_budget_allocated else 0.0


def growth_investment_ratio(growth_budget: float, total_budget: float) -> float:
    return growth_budget / total_budget if total_budget else 0.0


def reserve_ratio(reserve_cash: float, cash_available: float) -> float:
    return reserve_cash / cash_available if cash_available else 0.0


def operating_margin(revenue: float, operating_expenses: float) -> float:
    return (revenue - operating_expenses) / revenue if revenue else 0.0


# The three below are taken verbatim from each decision's own "formula" field in
# finance_rules.json (FIN-003, FIN-005, FIN-006) -- distinct from the engine_formulas above,
# which are general quarter-level formulas, not decision-specific.


def remaining_cash_after_capex(cash: float, capex: float) -> float:
    """FIN-003 Capital Expenditure: 'cash - capex'."""
    return cash - capex


def cash_after_debt_utilisation(cash: float, loan: float) -> float:
    """FIN-005 Debt Utilisation: 'cash + loan'."""
    return cash + loan


def total_hiring_budget(payroll: float, new_salaries: float) -> float:
    """FIN-006 Hiring Budget Approval: 'payroll + new_salaries'."""
    return payroll + new_salaries
