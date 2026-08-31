"""
planner.py

The recommendation engine.

Loads destination data, calculates an itemized trip cost, filters out
trips that are over budget, and ranks the remaining destinations using
the WeyWeGoing Score.
"""

import json

from scoring import calculate_weywegoing_score

DATA_PATH = "data/destinations.json"


def load_destinations(path=DATA_PATH):
    with open(path, "r") as file:
        return json.load(file)


def calculate_trip_cost(destination, days):
    """Returns an itemized estimated trip cost in TTD."""
    costs = destination["costs"]

    nights = max(days - 1, 0)

    accommodation = (
        costs["accommodation_per_night_ttd"] * nights
    )

    food = (
        costs["food_per_day_ttd"] * days
    )

    transport = (
        costs["transport_per_day_ttd"] * days
    )

    activities = (
        costs["activities_per_day_ttd"] * days
    )

    flight = destination["estimated_flight_ttd"]

    total = (
        flight
        + accommodation
        + food
        + transport
        + activities
    )

    return {
        "flight": flight,
        "accommodation": accommodation,
        "food": food,
        "transport": transport,
        "activities": activities,
        "total": total,
    }


def recommend_destinations(
    budget,
    days,
    preferences=None,
    max_results=3
):
    """Returns the best destinations that fit the user's budget."""
    preferences = preferences or {}
    destinations = load_destinations()

    results = []

    for destination in destinations:
        cost_breakdown = calculate_trip_cost(
            destination,
            days
        )

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
            "currency": destination["currency"],
            "cost_breakdown": cost_breakdown,
            "score_breakdown": score_breakdown,
            "buffer_remaining": budget - total_cost,
        })

    results.sort(
        key=lambda result: result["score_breakdown"]["final_score"],
        reverse=True
    )

    return results[:max_results]
