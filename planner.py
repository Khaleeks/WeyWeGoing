"""
planner.py

The recommendation engine.

destinations.json now contains only:
- destination identity
- country / territory information
- airport
- currency
- temporary preference scores

It no longer contains made-up flight, hotel, food, transport, or
activity prices.

Until a real pricing API is connected, budget is accepted as user
context but does NOT affect ranking.

Current ranking uses:
1. destination preference match
2. route convenience when known
3. real WeatherAPI forecast when an exact near-term date is supplied
"""

import json

from scoring import calculate_weywegoing_score
from weather_service import get_weather_for_date

DESTINATIONS_PATH = "data/destinations.json"
ROUTES_PATH = "data/routes.json"

def load_json(path):
    with open(path, "r") as file:
        return json.load(file)


def load_destinations(path=DESTINATIONS_PATH):
    return load_json(path)


def load_routes(path=ROUTES_PATH):
    return load_json(path)

def find_route(origin, destination, routes):
    """
    Finds a direct route first, then a simple one-stop route.

    If no route exists in the CURRENT SEEDED route dataset, the route is
    marked unknown rather than the destination being removed. This is
    important because routes.json does not yet cover the whole Caribbean.
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

    return {
        "route_type": "unknown",
        "legs": [],
    }


def recommend_destinations(
    days,
    preferences=None,
    origin="POS",
    travel_date=None,
    budget=None,
    max_results=3
):
    """
    Returns ranked Caribbean destination recommendations.

    budget is accepted so the agent can keep the user's stated budget in
    the request, but it is not evaluated until real pricing data is added.

    travel_date should be YYYY-MM-DD when supplied.
    """
    preferences = preferences or {}

    destinations = load_destinations()
    routes = load_routes()

    results = []

    for destination in destinations:
        if destination["airport"] == origin:
            continue

        route = find_route(
            origin,
            destination["airport"],
            routes
        )

        weather = None

        if travel_date:
            try:
                weather = get_weather_for_date(
                    destination["airport"],
                    travel_date
                )
            except Exception:
                # Weather failure should not make recommendations fail.
                weather = None

        score_breakdown = calculate_weywegoing_score(
            destination_scores=destination["scores"],
            user_preferences=preferences,
            route_type=route["route_type"],
            weather=weather,
        )

        results.append({
            "name": destination["name"],
            "country": destination["country"],
            "country_code": destination["country_code"],
            "region_type": destination["region_type"],
            "airport": destination["airport"],
            "currency": destination["currency"],
            "score_breakdown": score_breakdown,
            "route": route,
            "weather": weather,
            "travel_date": travel_date,
        })

    results.sort(
        key=lambda result: (
            result["score_breakdown"]["final_score"]
        ),
        reverse=True
    )

    return results[:max_results]
