"""
budget.py

Deterministic budget math. No LLM involvement.

Scope for this MVP: flight cost only. Accommodation, food, local
transport, and activities are NOT priced anywhere in this project, so
this module always says so explicitly rather than implying a whole-trip
budget fit from airfare alone.
"""

from currency_service import convert_currency


def evaluate_flight_budget(
    budget_amount,
    budget_currency,
    budget_scope,
    travelers,
    flight_price_total,
    flight_currency
):
    """
    Compares a flight quote against the user's stated budget.

    flight_price_total is the TOTAL price already returned by the flight
    provider for `travelers` travelers (Amadeus prices offers for the
    whole party, not per person).

    budget_scope is "per_person" or "group".

    Returns a dict describing the comparison. Never claims the whole trip
    fits - only ever comments on the flight portion.
    """
    budget_currency = (budget_currency or "USD").upper()
    flight_currency = (flight_currency or "USD").upper()

    if flight_currency == budget_currency:
        flight_total_in_budget_currency = flight_price_total
        conversion_rate = 1.0
        conversion_date = None
    else:
        converted = convert_currency(
            flight_price_total,
            flight_currency,
            budget_currency,
        )

        flight_total_in_budget_currency = converted["converted_amount"]
        conversion_rate = converted["rate"]
        conversion_date = converted["date"]

    per_person_flight_cost = flight_total_in_budget_currency / max(
        travelers, 1
    )

    if budget_scope == "per_person":
        amount_compared = per_person_flight_cost
    else:
        amount_compared = flight_total_in_budget_currency

    within_budget = None
    remaining = None

    if budget_amount is not None:
        remaining = round(budget_amount - amount_compared, 2)
        within_budget = amount_compared <= budget_amount

    return {
        "budget_amount": budget_amount,
        "budget_currency": budget_currency,
        "budget_scope": budget_scope,
        "travelers": travelers,
        "flight_total_group": round(flight_total_in_budget_currency, 2),
        "flight_total_per_person": round(per_person_flight_cost, 2),
        "amount_compared_to_budget": round(amount_compared, 2),
        "within_budget_for_flights_only": within_budget,
        "remaining_after_flights": remaining,
        "conversion_rate": conversion_rate,
        "conversion_date": conversion_date,
        "excluded_expenses": [
            "accommodation",
            "food",
            "local transport",
            "activities",
        ],
        "disclaimer": (
            "This only compares flight cost to the stated budget. It "
            "does not mean the whole trip fits the budget - "
            "accommodation, food, local transport, and activities are "
            "not priced by this prototype."
        ),
    }
