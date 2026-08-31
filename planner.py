"""
planner.py

The recommendation engine.

A destination now has to:
1. fit the user's budget
2. be reachable from the user's origin
3. match their interests

If a travel month is provided, seeded weather also affects the score.

Currency does not affect the numerical score. Instead, the remaining
TTD spending buffer is converted into the destination's local currency.
"""

import json

from scoring import calculate_weywegoing_score

DESTINATIONS_PATH = "data/destinations.json"
ROUTES_PATH = "data/routes.json"
WEATHER_PATH = "data/weather.json"
CURRENCY_PATH = "data/currency.json"


def load_json(path):
    with open(path, "r") as file:
        return json.load(file)


def load_destinations(path=DESTINATIONS_PATH):
    return load_json(path)


def load_routes(path=ROUTES_PATH):
    return load_json(path)


def load_weather(path=WEATHER_PATH):
    return load_json(path)


def load_currency(path=CURRENCY_PATH):
    return load_json(path)


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
        connection = first_leg["destination"]

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


def get_month_weather(destination_name, month, weather_data):
    """Returns seeded weather for one destination/month."""
    if not month:
        return None

    month = month.lower()

    for destination_weather in weather_data:
        if (
            destination_weather["destination"].lower()
            == destination_name.lower()
        ):
            return destination_weather["months"].get(month)

    return None


def convert_ttd_to_local(amount_ttd, currency_code, currency_data):
    """Converts TTD into a destination's local currency."""
    rates_to_ttd = currency_data["rates_to_ttd"]

    if currency_code not in rates_to_ttd:
        return None

    return round(
        amount_ttd / rates_to_ttd[currency_code],
        2
    )


def recommend_destinations(
    budget,
    days,
    preferences=None,
    origin="POS",
    month=None,
    max_results=3
):
    """
    Returns ranked destinations using budget, destination fit, route
    convenience, and optional weather.

    origin should be an airport code, e.g. POS.
    month is optional, e.g. "february".
    """
    preferences = preferences or {}

    destinations = load_destinations()
    routes = load_routes()
    weather_data = load_weather()
    currency_data = load_currency()

    results = []

    for destination in destinations:
        # Do not recommend the user's starting airport as the destination.
        if destination["airport"] == origin:
            continue

        route = find_route(
            origin,
            destination["airport"],
            routes
        )

        # If we cannot find a route in our dataset, do not recommend it.
        if route is None:
            continue

        cost_breakdown = calculate_trip_cost(
            destination,
            days
        )

        total_cost = cost_breakdown["total"]

        if total_cost > budget:
            continue

        weather = get_month_weather(
            destination["name"],
            month,
            weather_data
        )

        score_breakdown = calculate_weywegoing_score(
            total_cost=total_cost,
            budget=budget,
            destination_scores=destination["scores"],
            user_preferences=preferences,
            route_type=route["route_type"],
            weather=weather,
        )

        buffer_remaining = budget - total_cost

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
            "weather_month": month.lower() if month else None,
            "buffer_remaining": buffer_remaining,
            "buffer_local_currency": local_buffer,
        })

    results.sort(
        key=lambda result: result["score_breakdown"]["final_score"],
        reverse=True
    )

    return results[:max_results]
