"""
scoring.py

The WeyWeGoing Score.

The score is deterministic Python arithmetic. The LLM does not create
or change it.

Current heuristic weights:
- budget_fit: 25%
- preference_match: 40%
- route_convenience: 20%
- weather_fit: 15%

These are prototype product assumptions, not scientifically proven
weights. They can later be validated with user research and evaluation.
"""

WEIGHTS = {
    "budget_fit": 0.25,
    "preference_match": 0.40,
    "route_convenience": 0.20,
    "weather_fit": 0.15,
}


def score_budget_fit(total_cost, budget):
    """Returns a 0-100 score for how well the trip fits the budget."""
    if budget <= 0:
        return 0

    ratio = total_cost / budget

    if ratio > 1.0:
        return 0

    if ratio >= 0.7:
        return 100 - ((ratio - 0.7) / 0.3) * 20

    return 80 * (ratio / 0.7)


def score_preference_match(
    destination_scores,
    user_preferences
):
    """Returns a 0-100 match between destination and user interests."""
    if not user_preferences:
        return 60

    positive_preferences = {
        category: weight
        for category, weight in user_preferences.items()
        if weight > 0
    }

    if not positive_preferences:
        return 60

    total_weight = sum(
        positive_preferences.values()
    )

    weighted_sum = 0

    for category, weight in positive_preferences.items():
        destination_value = destination_scores.get(
            category,
            5
        )

        weighted_sum += (
            weight
            * (destination_value / 10)
            * 100
        )

    return weighted_sum / total_weight


def score_route_convenience(route_type):
    """Direct routes score higher than one-stop routes."""
    if route_type == "direct":
        return 100

    if route_type == "one_stop":
        return 70

    return 0


def score_weather_fit(weather):
    """
    Scores real forecast weather using chance of rain.

    If no usable forecast exists for the user's travel date, return a
    neutral score so weather does not unfairly help or hurt the trip.
    """
    if weather is None:
        return 60

    rain_probability = weather.get(
        "rain_probability"
    )

    if rain_probability is None:
        return 60

    if rain_probability <= 20:
        return 100

    if rain_probability <= 40:
        return 85

    if rain_probability <= 60:
        return 65

    if rain_probability <= 80:
        return 45

    return 25


def calculate_weywegoing_score(
    total_cost,
    budget,
    destination_scores,
    user_preferences,
    route_type,
    weather=None
):
    """Combines all current score components into one final score."""
    budget_component = score_budget_fit(
        total_cost,
        budget
    )

    preference_component = score_preference_match(
        destination_scores,
        user_preferences
    )

    route_component = score_route_convenience(
        route_type
    )

    weather_component = score_weather_fit(
        weather
    )

    final_score = (
        budget_component * WEIGHTS["budget_fit"]
        + preference_component * WEIGHTS["preference_match"]
        + route_component * WEIGHTS["route_convenience"]
        + weather_component * WEIGHTS["weather_fit"]
    )

    return {
        "final_score": round(final_score, 1),
        "budget_fit": round(
            budget_component,
            1
        ),
        "preference_match": round(
            preference_component,
            1
        ),
        "route_convenience": round(
            route_component,
            1
        ),
        "weather_fit": round(
            weather_component,
            1
        ),
    }
