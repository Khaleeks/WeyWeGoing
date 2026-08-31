"""
scoring.py

The WeyWeGoing Score. This is plain, deterministic arithmetic -- the
LLM never generates or influences the number itself. That separation
matters for the eventual eval suite: you can test this function with
no API calls at all, and it's the part of the system you can defend
as "grounded" rather than "the AI vibes it out".

Score components (each 0-100 before weighting):
- budget_fit: how comfortably the trip fits inside budget
- preference_match: weighted match against the user's stated interests
- (flight_convenience and weather are left as clearly-marked hooks
  for when routes.json / a weather tool exist -- see NEXT STEPS)
"""

WEIGHTS = {
    "budget_fit": 0.40,
    "preference_match": 0.60,
}


def score_budget_fit(total_cost, budget):
    """
    Rewards trips that use the budget efficiently without blowing it.
    A trip costing ~70-90% of budget scores highest (leaves a safety
    buffer without being wasteful); right at 100% scores lower;
    anything over budget should already have been filtered out
    upstream, but this is defensive.
    """
    if budget <= 0:
        return 0

    ratio = total_cost / budget

    if ratio > 1.0:
        return 0
    if ratio >= 0.7:
        # Sweet spot: 70-100% of budget used
        return 100 - ((ratio - 0.7) / 0.3) * 20  # scales 100 -> 80
    # Under 70% used: still fine, gently reward more efficiently
    return 80 * (ratio / 0.7)


def score_preference_match(destination_scores, user_preferences):
    """
    destination_scores: dict like {"beach": 9, "nightlife": 6, ...} (0-10 scale)
    user_preferences: dict like {"beach": 0.9, "nightlife": 0.7} (0-1 weights)

    Returns 0-100. If the user expressed no preferences at all,
    returns a neutral 60 so a trip isn't unfairly punished.
    """
    if not user_preferences:
        return 60

    total_weight = sum(user_preferences.values())
    if total_weight == 0:
        return 60

    weighted_sum = 0
    for category, weight in user_preferences.items():
        destination_value = destination_scores.get(category, 5)  # neutral default
        weighted_sum += weight * (destination_value / 10) * 100

    return weighted_sum / total_weight


def calculate_weywegoing_score(total_cost, budget, destination_scores, user_preferences):
    """
    Combines components into the final 0-100 WeyWeGoing Score.

    NEXT STEPS (not yet implemented -- see README):
    - flight_convenience: once routes.json models direct vs
      connecting flights, add a component here and rebalance WEIGHTS.
    - weather: once a weather tool exists, add a component that
      lowers the score for destinations with poor forecasts during
      the user's travel dates.
    """
    budget_component = score_budget_fit(total_cost, budget)
    preference_component = score_preference_match(destination_scores, user_preferences)

    final_score = (
        budget_component * WEIGHTS["budget_fit"]
        + preference_component * WEIGHTS["preference_match"]
    )

    return {
        "final_score": round(final_score, 1),
        "budget_fit": round(budget_component, 1),
        "preference_match": round(preference_component, 1),
    }
