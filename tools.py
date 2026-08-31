"""
tools.py

Defines the tools WeyWeGoing?'s LLM can choose to call.

The recommendation tool now uses destination, route, weather, and
currency data together. The other tools still let the agent answer
specific follow-up questions.
"""

import json

from planner import (
    load_currency,
    load_destinations,
    load_routes,
    load_weather,
    find_route,
    recommend_destinations as _recommend_destinations
)

ROUTES_PATH = "data/routes.json"
WEATHER_PATH = "data/weather.json"
CURRENCY_PATH = "data/currency.json"


def _normalize_place(place):
    """Turns common place names into airport codes."""
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
    preferences=None,
    origin="POS",
    month=None
):
    """Returns ranked destination recommendations."""
    origin_code = _normalize_place(origin)

    results = _recommend_destinations(
        budget=budget,
        days=days,
        preferences=preferences or {},
        origin=origin_code,
        month=month,
    )

    if not results:
        return {
            "status": "no_matches",
            "results": []
        }

    return {
        "status": "ok",
        "origin": origin_code,
        "month": month,
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
    """Checks seeded route data between two Caribbean places."""
    routes = load_routes()

    origin_code = _normalize_place(origin)
    destination_code = _normalize_place(destination)

    route = find_route(
        origin_code,
        destination_code,
        routes
    )

    if route is None:
        return {
            "status": "not_found",
            "message": (
                f"No direct or one-stop seeded route found "
                f"from {origin_code} to {destination_code}."
            ),
        }

    return {
        "status": "ok",
        "origin": origin_code,
        "destination": destination_code,
        **route,
    }


def get_weather_tool(destination, month):
    """Returns seeded typical weather for a destination and month."""
    weather_data = load_weather()

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
            }

    return {
        "status": "not_found",
        "message": f"No weather data for '{destination}'.",
    }


def convert_currency_tool(
    amount,
    from_currency,
    to_currency
):
    """Converts money using seeded demo exchange rates."""
    currency_data = load_currency()
    rates_to_ttd = currency_data["rates_to_ttd"]

    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": f"No seeded rate for {from_code}.",
        }

    if to_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": f"No seeded rate for {to_code}.",
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
                "Recommend Caribbean destinations for a NEW trip request. "
                "This tool checks budget, destination preferences, route "
                "convenience, and weather when a month is provided. "
                "Default origin is Trinidad (POS) unless the user says otherwise."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {
                        "type": "integer",
                        "description": "Total trip budget in TTD.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Length of the trip in days.",
                    },
                    "origin": {
                        "type": "string",
                        "description": (
                            "Starting place or airport code. "
                            "Use POS for Trinidad by default."
                        ),
                    },
                    "month": {
                        "type": "string",
                        "description": (
                            "Travel month, e.g. February. "
                            "Only include it if the user gave a month."
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
                        "description": "Destination name.",
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
                "Check whether a direct or one-stop route exists "
                "between two places in the seeded route data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Origin place or airport code.",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination place or airport code.",
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
                "Get SEEDED TYPICAL weather for a destination "
                "in a specific month. This is not a live forecast."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Destination name.",
                    },
                    "month": {
                        "type": "string",
                        "description": "Month name.",
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
                "Convert money between supported currencies using "
                "SEEDED DEMO exchange rates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": "Amount to convert.",
                    },
                    "from_currency": {
                        "type": "string",
                        "description": "Source currency code.",
                    },
                    "to_currency": {
                        "type": "string",
                        "description": "Target currency code.",
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
