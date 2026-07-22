"""Product workspace engine formulas, taken verbatim from product_rules.json's core_formulas."""


def product_quality(base_quality: float, qa_investment: float, rnd_bonus: float, technical_debt: float) -> float:
    return base_quality + qa_investment + rnd_bonus - technical_debt


def feature_completion(completed_features: float, planned_features: float) -> float:
    return completed_features / planned_features * 100 if planned_features else 0.0


def innovation_score(rnd_investment: float, new_features: float, technology_adoption: float) -> float:
    return rnd_investment + new_features + technology_adoption


def product_readiness(development: float, testing: float, manufacturing: float) -> float:
    return (development + testing + manufacturing) / 3


def product_rating(customer_experience: float, quality: float, reliability: float) -> float:
    return customer_experience + quality + reliability


def demand_score(market_fit: float, brand_awareness: float, marketing_impact: float) -> float:
    return market_fit + brand_awareness + marketing_impact


def product_health(quality: float, customer_satisfaction: float, demand: float) -> float:
    return quality + customer_satisfaction + demand


def product_development_cost(feature_cost: float, rnd_cost: float, testing_cost: float) -> float:
    return feature_cost + rnd_cost + testing_cost


def time_to_market(remaining_development: float, development_velocity: float) -> float:
    return remaining_development / development_velocity if development_velocity else float("inf")


def product_roi(revenue_generated: float, development_cost: float) -> float:
    return revenue_generated - development_cost
