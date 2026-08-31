"""
tools.py

Defines the tools WeyWeGoing?'s LLM can choose to call.

The LLM decides WHICH tool it needs. The Python function behind the
tool then reads the relevant data file and returns structured data.

Current tools:
- recommend_destinations
- get_destination_details
- check_route
- get_weather
- convert_currency
"""

import json

from planner import (
    load_destinations,
    recommend_destinations as _recommend_destinations
)

ROUTES_PATH = "data/routes.json"
WEATHER_PATH = "data/weather.json"
CURRENCY_PATH = "data/currency.json"


def _load_json(path):
    """Loads one JSON data file."""
    with open(path, "r") as file:
        return json.load(file)


def _normalize_place(place):
    """Turns common place names into airport codes used by routes.json."""
    aliases = {
        "trinidad": "POS",
        "trinidad and tobago": "POS",
        "port of spain": "POS",
        "pos": "POS",
        "tobago": "TAB",
        "scarborough": "TAB",
        "tab": "TAB",
        "grenada": "GND",
        "gnd": "GND",
        "barbados": "BGI",
        "bgi": "BGI",
        "saint lucia": "SLU",
        "st lucia": "SLU",
        "st. lucia": "SLU",
        "slu": "SLU",
        "guyana": "GEO",
        "georgetown": "GEO",
        "geo": "GEO",
        "dominica": "DOM",
        "dom": "DOM",
        "antigua": "ANU",
        "antigua and barbuda": "ANU",
        "anu": "ANU",
        "jamaica": "KIN",
        "kingston": "KIN",
        "kin": "KIN",
    }

    cleaned = place.strip().lower()

    return aliases.get(
        cleaned,
        place.strip().upper()
    )


def recommend_destinations_tool(
    budget,
    days,
    preferences=None
):
    """Returns ranked destination recommendations."""
    results = _recommend_destinations(
        budget=budget,
        days=days,
        preferences=preferences or {},
    )

    if not results:
        return {
            "status": "no_matches",
            "results": []
        }

    return {
        "status": "ok",
        "results": results
    }


def get_destination_details_tool(name):
    """Looks up one destination in destinations.json."""
    destinations = load_destinations()

    for destination in destinations:
        if destination["name"].lower() == name.lower():
            return {
                "status": "ok",
                "destination": destination
            }

    return {
        "status": "not_found",
        "message": (
            f"No destination named '{name}' "
            "in the current dataset."
        ),
        "available_destinations": [
            destination["name"]
            for destination in destinations
        ],
    }


def check_route_tool(origin, destination):
    """Checks seeded route data between two Caribbean airports."""
    routes = _load_json(ROUTES_PATH)

    origin_code = _normalize_place(origin)
    destination_code = _normalize_place(destination)

    direct_routes = [
        route
        for route in routes
        if route["origin"] == origin_code
        and route["destination"] == destination_code
    ]

    if direct_routes:
        return {
            "status": "ok",
            "route_type": "direct",
            "origin": origin_code,
            "destination": destination_code,
            "routes": direct_routes,
        }

    # Simple one-stop search.
    first_legs = [
        route
        for route in routes
        if route["origin"] == origin_code
    ]

    for first_leg in first_legs:
        connection = first_leg["destination"]

        second_legs = [
            route
            for route in routes
            if route["origin"] == connection
            and route["destination"] == destination_code
        ]

        if second_legs:
            return {
                "status": "ok",
                "route_type": "one_stop",
                "origin": origin_code,
                "destination": destination_code,
                "connection": connection,
                "first_leg": first_leg,
                "second_leg": second_legs[0],
            }

    return {
        "status": "not_found",
        "message": (
            f"No direct or one-stop seeded route found "
            f"from {origin_code} to {destination_code}."
        ),
    }


def get_weather_tool(destination, month):
    """Returns seeded typical weather for a destination and month."""
    weather_data = _load_json(WEATHER_PATH)

    for destination_weather in weather_data:
        if (
            destination_weather["destination"].lower()
            == destination.lower()
        ):
            month_data = destination_weather["months"].get(
                month.lower()
            )

            if month_data:
                return {
                    "status": "ok",
                    "destination": destination_weather["destination"],
                    "month": month.lower(),
                    "weather": month_data,
                    "data_type": "seeded_typical_weather",
                }

            return {
                "status": "not_found",
                "message": (
                    f"No seeded weather data for {destination} "
                    f"in {month}."
                ),
                "available_months": list(
                    destination_weather["months"].keys()
                ),
            }

    return {
        "status": "not_found",
        "message": (
            f"No weather data for '{destination}'."
        ),
    }


def convert_currency_tool(
    amount,
    from_currency,
    to_currency
):
    """Converts money using seeded demo exchange rates."""
    currency_data = _load_json(CURRENCY_PATH)

    rates_to_ttd = currency_data["rates_to_ttd"]

    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": (
                f"No seeded rate for {from_code}."
            ),
        }

    if to_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": (
                f"No seeded rate for {to_code}."
            ),
        }

    amount_in_ttd = (
        amount * rates_to_ttd[from_code]
    )

    converted_amount = (
        amount_in_ttd / rates_to_ttd[to_code]
    )

    return {
        "status": "ok",
        "amount": amount,
        "from_currency": from_code,
        "to_currency": to_code,
        "converted_amount": round(
            converted_amount,
            2
        ),
        "data_type": "seeded_exchange_rate",
    }


TOOL_FUNCTIONS = {
    "recommend_destinations": recommend_destinations_tool,
    "get_destination_details": get_destination_details_tool,
    "check_route": check_route_tool,
    "get_weather": get_weather_tool,
    "convert_currency": convert_currency_tool,
}


TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_destinations",
            "description": (
                "Recommend Caribbean destinations for a NEW trip "
                "request. Use when the user provides a budget and "
                "trip length and wants to know where to go."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {
                        "type": "integer",
                        "description": (
                            "Total trip budget in TTD."
                        ),
                    },
                    "days": {
                        "type": "integer",
                        "description": (
                            "Length of the trip in days."
                        ),
                    },
                    "preferences": {
                        "type": "object",
                        "description": (
                            "Weighted interests from 0.0 to 1.0."
                        ),
                        "properties": {
                            "beach": {"type": "number"},
                            "nightlife": {"type": "number"},
                            "food": {"type": "number"},
                            "culture": {"type": "number"},
                            "nature": {"type": "number"},
                            "romantic": {"type": "number"},
                            "adventure": {"type": "number"},
                            "relaxation": {"type": "number"},
                        },
                    },
                },
                "required": [
                    "budget",
                    "days"
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_destination_details",
            "description": (
                "Get the stored details for ONE specific "
                "Caribbean destination."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Destination name, for example Grenada."
                        ),
                    },
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_route",
            "description": (
                "Check whether a direct or simple one-stop route "
                "exists between two places in the seeded route data. "
                "Use for questions about flights or connections."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": (
                            "Origin place or airport code."
                        ),
                    },
                    "destination": {
                        "type": "string",
                        "description": (
                            "Destination place or airport code."
                        ),
                    },
                },
                "required": [
                    "origin",
                    "destination"
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get SEEDED TYPICAL weather for a Caribbean "
                "destination in a specific month. This is not a "
                "live forecast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": (
                            "Destination name."
                        ),
                    },
                    "month": {
                        "type": "string",
                        "description": (
                            "Month name, for example October."
                        ),
                    },
                },
                "required": [
                    "destination",
                    "month"
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": (
                "Convert an amount between supported Caribbean "
                "currencies using SEEDED DEMO exchange rates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": (
                            "Amount of money to convert."
                        ),
                    },
                    "from_currency": {
                        "type": "string",
                        "description": (
                            "Three-letter source currency code."
                        ),
                    },
                    "to_currency": {
                        "type": "string",
                        "description": (
                            "Three-letter target currency code."
                        ),
                    },
                },
                "required": [
                    "amount",
                    "from_currency",
                    "to_currency"
                ],
            },
        },
    },
]
