"""
planner.py

The recommendation engine.

A destination must:
1. fit the user's budget
2. be reachable from the user's origin
3. match the user's interests

If the user supplies an exact travel date and that date is inside
WeatherAPI's available forecast window, real weather also affects the
score.

Currency does not affect the numerical score. The remaining TTD buffer
is converted into the destination's local currency for useful context.
"""

import json

from scoring import calculate_weywegoing_score
from weather_service import get_weather_for_date

DESTINATIONS_PATH = "data/destinations.json"
ROUTES_PATH = "data/routes.json"
CURRENCY_PATH = "data/currency.json"


def load_json(path):
    with open(path, "r") as file:
        return json.load(file)


def load_destinations(path=DESTINATIONS_PATH):
    return load_json(path)


def load_routes(path=ROUTES_PATH):
    return load_json(path)


def load_currency(path=CURRENCY_PATH):
    return load_json(path)


def calculate_trip_cost(destination, days):
    """Returns an itemized estimated trip cost in TTD."""
    costs = destination["costs"]
    nights = max(days - 1, 0)

    accommodation = (
        costs["accommodation_per_night_ttd"]
        * nights
    )

    food = (
        costs["food_per_day_ttd"]
        * days
    )

    transport = (
        costs["transport_per_day_ttd"]
        * days
    )

    activities = (
        costs["activities_per_day_ttd"]
        * days
    )

    flight = destination[
        "estimated_flight_ttd"
    ]

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


def find_route(origin, destination, routes):
    """
    Finds a direct route first, then a simple one-stop route.

    Returns None when the destination is not reachable in the seeded
    route data.
    """
    direct_routes = [
        route
        for route in routes
        if route["origin"] == origin
        and route["destination"] == destination
    ]

    if direct_routes:
        return {
            "route_type": "direct",
            "legs": [direct_routes[0]],
        }

    first_legs = [
        route
        for route in routes
        if route["origin"] == origin
    ]

    for first_leg in first_legs:
        connection = first_leg[
            "destination"
        ]

        second_legs = [
            route
            for route in routes
            if route["origin"] == connection
            and route["destination"] == destination
        ]

        if second_legs:
            return {
                "route_type": "one_stop",
                "connection": connection,
                "legs": [
                    first_leg,
                    second_legs[0]
                ],
            }

    return None


def convert_ttd_to_local(
    amount_ttd,
    currency_code,
    currency_data
):
    """Converts TTD into a destination's local currency."""
    rates_to_ttd = currency_data[
        "rates_to_ttd"
    ]

    if currency_code not in rates_to_ttd:
        return None

    return round(
        amount_ttd
        / rates_to_ttd[currency_code],
        2
    )


def recommend_destinations(
    budget,
    days,
    preferences=None,
    origin="POS",
    travel_date=None,
    max_results=3
):
    """
    Returns ranked destination recommendations.

    travel_date should be YYYY-MM-DD when supplied.

    WeatherAPI's free plan provides a 3-day forecast. If travel_date is
    not inside that forecast window, weather remains neutral.
    """
    preferences = preferences or {}

    destinations = load_destinations()
    routes = load_routes()
    currency_data = load_currency()

    results = []

    for destination in destinations:
        if destination["airport"] == origin:
            continue

        route = find_route(
            origin,
            destination["airport"],
            routes
        )

        if route is None:
            continue

        cost_breakdown = calculate_trip_cost(
            destination,
            days
        )

        total_cost = cost_breakdown["total"]

        if total_cost > budget:
            continue

        weather = None

        if travel_date:
            try:
                weather = get_weather_for_date(
                    destination["airport"],
                    travel_date
                )
            except Exception:
                # Weather should not make the whole recommendation fail.
                # If the API is unavailable, use the neutral weather score.
                weather = None

        score_breakdown = calculate_weywegoing_score(
            total_cost=total_cost,
            budget=budget,
            destination_scores=destination["scores"],
            user_preferences=preferences,
            route_type=route["route_type"],
            weather=weather,
        )

        buffer_remaining = (
            budget - total_cost
        )

        local_buffer = convert_ttd_to_local(
            buffer_remaining,
            destination["currency"],
            currency_data
        )

        results.append({
            "name": destination["name"],
            "airport": destination["airport"],
            "currency": destination["currency"],
            "cost_breakdown": cost_breakdown,
            "score_breakdown": score_breakdown,
            "route": route,
            "weather": weather,
            "travel_date": travel_date,
            "buffer_remaining": buffer_remaining,
            "buffer_local_currency": local_buffer,
        })

    results.sort(
        key=lambda result: (
            result["score_breakdown"][
                "final_score"
            ]
        ),
        reverse=True
    )

    return results[:max_results]
