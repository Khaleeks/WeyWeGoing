"""
formatting.py

Shared, presentation-only helpers used by both the CLI (main.py) and the
Streamlit app (streamlit_app.py), so cost/flight/budget labeling stays
consistent (and honest) across both front ends. No business logic lives
here - just turning already-computed dicts into readable text.
"""


def format_money(amount, currency):
    if amount is None:
        return "unknown"

    return f"{amount:,.2f} {currency}"


def flight_headline(flight):
    """One-line summary of a flight quote/estimate, always naming its
    source so a demo estimate can never be mistaken for a live price."""
    if flight is None:
        return "No exact travel date given, so no flight quote was fetched."

    if flight.get("status") == "error":
        return f"Flight quote failed: {flight.get('message', 'unknown error')}"

    if flight.get("status") == "no_results":
        return f"No flight offers found: {flight.get('message', '')}"

    price_line = format_money(
        flight.get("price_total"),
        flight.get("currency"),
    )

    if flight.get("data_type") == "demo_estimate":
        label = "DEMO estimate (not a real fare)"
    else:
        label = "sandbox test-environment quote (not production pricing)"

    travelers = flight.get("travelers", 1)

    return (
        f"Flights ~{price_line} total for {travelers} traveler(s) - "
        f"{label}, retrieved {flight.get('retrieved_at')}."
    )


def budget_line(budget_evaluation):
    if budget_evaluation is None:
        return None

    scope = budget_evaluation["budget_scope"]
    amount_compared = format_money(
        budget_evaluation["amount_compared_to_budget"],
        budget_evaluation["budget_currency"],
    )
    budget_amount = format_money(
        budget_evaluation["budget_amount"],
        budget_evaluation["budget_currency"],
    )

    fits = budget_evaluation["within_budget_for_flights_only"]
    verdict = "within" if fits else "OVER"

    scope_label = "per person" if scope == "per_person" else "for the group"

    return (
        f"Flights only ({scope_label}): {amount_compared} vs budget "
        f"{budget_amount} -> {verdict} budget for flights. "
        f"Excludes: {', '.join(budget_evaluation['excluded_expenses'])}."
    )


def missing_info_questions(missing_fields):
    return [item["question"] for item in missing_fields]


def provider_mode_banner(status):
    """One line per provider describing live vs demo/unavailable mode."""
    lines = []

    labels = {
        "llm": "Agent (Groq LLM)",
        "weather": "Weather (WeatherAPI.com)",
        "flights": "Flights (Amadeus)",
        "currency": "Currency (Frankfurter)",
    }

    for key, label in labels.items():
        mode = status[key]["mode"]
        lines.append(f"  {label}: {mode.upper()}")

    return "\n".join(lines)
