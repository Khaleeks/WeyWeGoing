"""
planner.py

The recommendation engine. Loads destinations, calculates a real
itemized trip cost for each (not just flight + flat daily rate), and
ranks them using scoring.py's WeyWeGoing Score.

No LLM calls happen in this file -- everything here is testable with
plain unit tests and no API key, which is exactly what you want for
the eval suite later.
"""

import json

from scoring import calculate_weywegoing_score

DATA_PATH = "data/destinations.json"


def load_destinations(path=DATA_PATH):
    with open(path, "r") as file:
        return json.load(file)


def calculate_trip_cost(destination, days):
    """
    Returns an itemized cost breakdown, not just a total -- this is
    what lets main.py print a real "Estimated Total Trip" receipt
    instead of a single opaque number.
    """
    costs = destination["costs"]
    nights = max(days - 1, 0)  # a 3-day trip is usually 2 nights

    accommodation = costs["accommodation_per_night_ttd"] * nights
    food = costs["food_per_day_ttd"] * days
    transport = costs["transport_per_day_ttd"] * days
    activities = costs["activities_per_day_ttd"] * days
    flight = destination["estimated_flight_ttd"]

    total = flight + accommodation + food + transport + activities

    return {
        "flight": flight,
        "accommodation": accommodation,
        "food": food,
        "transport": transport,
        "activities": activities,
        "total": total,
    }


def recommend_destinations(budget, days, preferences=None, max_results=3):
    """
    budget: int, TTD
    days: int
    preferences: dict like {"beach": 0.9, "nightlife": 0.7} or None

    Returns a list of recommendation dicts, sorted by WeyWeGoing Score
    descending, capped at max_results.
    """
    preferences = preferences or {}
    destinations = load_destinations()

    results = []

    for destination in destinations:
        cost_breakdown = calculate_trip_cost(destination, days)
        total_cost = cost_breakdown["total"]

        if total_cost > budget:
            continue

        score_breakdown = calculate_weywegoing_score(
            total_cost=total_cost,
            budget=budget,
            destination_scores=destination["scores"],
            user_preferences=preferences,
        )

        results.append({
            "name": destination["name"],
            "airport": destination["airport"],
            "cost_breakdown": cost_breakdown,
            "score_breakdown": score_breakdown,
            "buffer_remaining": budget - total_cost,
        })

    results.sort(key=lambda r: r["score_breakdown"]["final_score"], reverse=True)

    return results[:max_results]
