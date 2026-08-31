"""
scoring.py

The WeyWeGoing Score.

The score is deterministic Python arithmetic. The LLM does not create
or change it.

Score components:
- budget_fit: how well the trip fits the user's budget
- preference_match: how well the destination matches their interests
- route_convenience: direct flight vs one-stop connection
- weather_fit: how suitable the seeded weather is for the trip

Currency is NOT scored. All trip costs are already compared in TTD,
so exchange rates are shown as useful context instead of being treated
as if one currency makes a destination better than another.
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


def score_preference_match(destination_scores, user_preferences):
    """Returns a 0-100 match between destination scores and interests."""
    if not user_preferences:
        return 60

    total_weight = sum(user_preferences.values())

    if total_weight == 0:
        return 60

    weighted_sum = 0

    for category, weight in user_preferences.items():
        destination_value = destination_scores.get(category, 5)
        weighted_sum += weight * (destination_value / 10) * 100

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
    Returns a simple 0-100 weather score from the seeded weather data.

    If no month was supplied, return a neutral score so weather does not
    unfairly help or hurt the destination.
    """
    if weather is None:
        return 60

    rain_scores = {
        "low": 100,
        "medium": 75,
        "high": 45,
    }

    beach_scores = {
        "excellent": 100,
        "good": 80,
        "fair": 55,
        "poor": 30,
    }

    rain_score = rain_scores.get(
        weather.get("rain_risk"),
        60
    )

    beach_score = beach_scores.get(
        weather.get("beach_suitability"),
        60
    )

    return (
        rain_score * 0.60
        + beach_score * 0.40
    )


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
        "budget_fit": round(budget_component, 1),
        "preference_match": round(preference_component, 1),
        "route_convenience": round(route_component, 1),
        "weather_fit": round(weather_component, 1),
    }
