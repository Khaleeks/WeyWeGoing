"""
tools.py

Defines the tools WeyWeGoing?'s LLM can choose to call.

Weather now comes from WeatherAPI.com instead of data/weather.json.
Route, currency, and destination data are still seeded for now.
"""

from planner import (
    load_currency,
    load_destinations,
    load_routes,
    find_route,
    recommend_destinations as _recommend_destinations
)
from weather_service import get_forecast


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
    travel_date=None
):
    """Returns ranked destination recommendations."""
    origin_code = _normalize_place(
        origin
    )

    results = _recommend_destinations(
        budget=budget,
        days=days,
        preferences=preferences or {},
        origin=origin_code,
        travel_date=travel_date,
    )

    if not results:
        return {
            "status": "no_matches",
            "results": []
        }

    return {
        "status": "ok",
        "origin": origin_code,
        "travel_date": travel_date,
        "results": results
    }


def get_destination_details_tool(name):
    """Looks up one destination in destinations.json."""
    destinations = load_destinations()

    for destination in destinations:
        if (
            destination["name"].lower()
            == name.lower()
        ):
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

    origin_code = _normalize_place(
        origin
    )

    destination_code = _normalize_place(
        destination
    )

    route = find_route(
        origin_code,
        destination_code,
        routes
    )

    if route is None:
        return {
            "status": "not_found",
            "message": (
                "No direct or one-stop seeded route "
                f"found from {origin_code} "
                f"to {destination_code}."
            ),
        }

    return {
        "status": "ok",
        "origin": origin_code,
        "destination": destination_code,
        **route,
    }


def get_weather_tool(destination, days=3):
    """
    Gets the real near-term forecast from WeatherAPI.com.

    The destination is matched against destinations.json so the tool can
    reuse the airport code already stored for that destination.
    """
    destinations = load_destinations()

    destination_data = None

    for item in destinations:
        if (
            item["name"].lower()
            == destination.lower()
        ):
            destination_data = item
            break

    if destination_data is None:
        return {
            "status": "not_found",
            "message": (
                f"No destination named "
                f"'{destination}' "
                "in the current dataset."
            ),
        }

    try:
        weather_data = get_forecast(
            destination_data["airport"],
            days
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }

    return {
        "status": "ok",
        "destination": destination_data["name"],
        "airport": destination_data["airport"],
        "data_type": "live_forecast",
        "location": weather_data["location"],
        "forecast": weather_data["forecast"],
    }


def convert_currency_tool(
    amount,
    from_currency,
    to_currency
):
    """Converts money using seeded demo exchange rates."""
    currency_data = load_currency()

    rates_to_ttd = currency_data[
        "rates_to_ttd"
    ]

    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": (
                f"No seeded rate for "
                f"{from_code}."
            ),
        }

    if to_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": (
                f"No seeded rate for "
                f"{to_code}."
            ),
        }

    amount_in_ttd = (
        amount
        * rates_to_ttd[from_code]
    )

    converted_amount = (
        amount_in_ttd
        / rates_to_ttd[to_code]
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
                "Recommend Caribbean destinations for a new trip. "
                "The tool checks budget, preferences and route "
                "convenience. If an exact travel date is provided "
                "and falls inside the available forecast window, "
                "real WeatherAPI forecast data also affects ranking. "
                "Default origin is Trinidad/POS."
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
                            "Length of trip in days."
                        ),
                    },
                    "origin": {
                        "type": "string",
                        "description": (
                            "Starting place or airport code. "
                            "Use POS by default."
                        ),
                    },
                    "travel_date": {
                        "type": "string",
                        "description": (
                            "Exact trip start date in YYYY-MM-DD "
                            "format. Only include when the user "
                            "provides an exact date."
                        ),
                    },
                    "preferences": {
                        "type": "object",
                        "description": (
                            "Only include interests the user "
                            "actually expressed, with weights "
                            "from 0.0 to 1.0."
                        ),
                        "properties": {
                            "beach": {
                                "type": "number"
                            },
                            "nightlife": {
                                "type": "number"
                            },
                            "food": {
                                "type": "number"
                            },
                            "culture": {
                                "type": "number"
                            },
                            "nature": {
                                "type": "number"
                            },
                            "romantic": {
                                "type": "number"
                            },
                            "adventure": {
                                "type": "number"
                            },
                            "relaxation": {
                                "type": "number"
                            },
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
                "Get stored details for one "
                "specific Caribbean destination."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": (
                            "Destination name."
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
                "Check whether a direct or one-stop "
                "route exists between two places in "
                "the seeded route data."
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
                "Get the real near-term weather forecast "
                "for a Caribbean destination using WeatherAPI.com. "
                "The free project integration supports up to 3 days."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": (
                            "Caribbean destination name."
                        ),
                    },
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                        "description": (
                            "Number of forecast days, "
                            "from 1 to 3."
                        ),
                    },
                },
                "required": [
                    "destination"
                ],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": (
                "Convert money between supported "
                "currencies using seeded demo rates."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "amount": {
                        "type": "number",
                        "description": (
                            "Amount to convert."
                        ),
                    },
                    "from_currency": {
                        "type": "string",
                        "description": (
                            "Source currency code."
                        ),
                    },
                    "to_currency": {
                        "type": "string",
                        "description": (
                            "Target currency code."
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
