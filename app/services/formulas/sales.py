"""Sales workspace engine formulas, taken verbatim from sales_rules.json's formulas + negotiation_engine."""


def revenue(units_sold: float, selling_price: float) -> float:
    return units_sold * selling_price


def average_selling_price(revenue_value: float, units_sold: float) -> float:
    return revenue_value / units_sold if units_sold else 0.0


def average_order_value(revenue_value: float, total_orders: float) -> float:
    return revenue_value / total_orders if total_orders else 0.0


def conversion_rate(orders: float, visitors: float) -> float:
    return orders / visitors * 100 if visitors else 0.0


def repeat_purchase_rate(repeat_customers: float, active_customers: float) -> float:
    return repeat_customers / active_customers * 100 if active_customers else 0.0


def customer_lifetime_value(aov: float, purchase_frequency: float, customer_lifespan: float) -> float:
    return aov * purchase_frequency * customer_lifespan


def revenue_forecast_accuracy(actual_revenue: float, forecast_revenue: float) -> float:
    return actual_revenue / forecast_revenue * 100 if forecast_revenue else 0.0


def channel_contribution(channel_revenue: float, total_revenue: float) -> float:
    return channel_revenue / total_revenue * 100 if total_revenue else 0.0


def discount_impact(discount_amount: float, revenue_value: float) -> float:
    return discount_amount / revenue_value * 100 if revenue_value else 0.0


def net_sales(gross_sales: float, discounts: float, returns: float) -> float:
    return gross_sales - discounts - returns


def negotiation_score(
    price_competitiveness: float,
    relationship_score: float,
    inventory_availability: float,
    brand_strength: float,
    delivery_capability: float,
    risk: float,
) -> float:
    return price_competitiveness + relationship_score + inventory_availability + brand_strength + delivery_capability - risk


def acceptance_probability(negotiation_score_value: float, buyer_flexibility: float, market_demand: float) -> float:
    return negotiation_score_value * buyer_flexibility * market_demand
