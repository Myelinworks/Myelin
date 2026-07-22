"""Customer Experience workspace engine formulas, taken verbatim from cx_rules.json's formulas."""


def csat(positive_experiences: float, total_experiences: float) -> float:
    return positive_experiences / total_experiences * 100 if total_experiences else 0.0


def nps(percent_promoters: float, percent_detractors: float) -> float:
    return percent_promoters - percent_detractors


def churn_rate(lost_customers: float, active_customers: float) -> float:
    return lost_customers / active_customers * 100 if active_customers else 0.0


def retention_rate(active_customers: float, previous_customers: float) -> float:
    return active_customers / previous_customers * 100 if previous_customers else 0.0


def referral_rate(referred_customers: float, active_customers: float) -> float:
    return referred_customers / active_customers * 100 if active_customers else 0.0


def product_adoption(active_feature_users: float, active_customers: float) -> float:
    return active_feature_users / active_customers * 100 if active_customers else 0.0


def customer_lifetime_value(average_order_value: float, purchase_frequency: float, customer_lifespan: float) -> float:
    return average_order_value * purchase_frequency * customer_lifespan


def brand_trust(previous_trust: float, positive_experiences: float, negative_experiences: float) -> float:
    return previous_trust + positive_experiences - negative_experiences


def community_growth(new_members: float, inactive_members: float) -> float:
    return new_members - inactive_members


def social_sentiment(positive_mentions: float, negative_mentions: float) -> float:
    return positive_mentions - negative_mentions
