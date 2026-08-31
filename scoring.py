"""
scoring.py

The WeyWeGoing Score.

The score is deterministic Python arithmetic. The LLM does not create
or change it.

Current V1 ranking:
- preference_match: 60%
- route_convenience: 25%
- weather_fit: 15%

Budget is NOT scored right now because destinations.json no longer
contains made-up trip prices. Budget scoring will return when WeyWeGoing?
is connected to a real flight/accommodation pricing source.

These weights are prototype heuristics and can be changed later.
"""

WEIGHTS = {
    "preference_match": 0.60,
    "route_convenience": 0.25,
    "weather_fit": 0.15,
}


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
    """
    Scores route convenience.

    'unknown' is neutral because routes.json is still incomplete.
    """
    if route_type == "direct":
        return 100

    if route_type == "one_stop":
        return 70

    return 50


def score_weather_fit(weather):
    """
    Scores real forecast weather using chance of rain.

    If no usable forecast exists for the user's exact travel date,
    return a neutral score.
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
    destination_scores,
    user_preferences,
    route_type,
    weather=None
):
    """Combines the current score components into one final score."""
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
        preference_component
        * WEIGHTS["preference_match"]
        + route_component
        * WEIGHTS["route_convenience"]
        + weather_component
        * WEIGHTS["weather_fit"]
    )

    return {
        "final_score": round(final_score, 1),
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
