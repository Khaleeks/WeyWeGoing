"""
tools.py

Defines the tools WeyWeGoing?'s LLM can choose to call.

Weather comes from WeatherAPI.com.

destinations.json is the Caribbean destination catalog.
Route and currency data are still seeded demo data for now.
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
    """Turns common place names into airport codes when known."""
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
        "bahamas": "NAS",
        "the bahamas": "NAS",
        "nassau": "NAS",
        "nas": "NAS",
        "cuba": "HAV",
        "havana": "HAV",
        "hav": "HAV",
        "dominican republic": "SDQ",
        "santo domingo": "SDQ",
        "sdq": "SDQ",
        "haiti": "PAP",
        "port-au-prince": "PAP",
        "pap": "PAP",
        "saint kitts and nevis": "SKB",
        "st kitts and nevis": "SKB",
        "skb": "SKB",
        "saint vincent and the grenadines": "SVD",
        "st vincent and the grenadines": "SVD",
        "svd": "SVD",
        "anguilla": "AXA",
        "axa": "AXA",
        "british virgin islands": "EIS",
        "eis": "EIS",
        "cayman islands": "GCM",
        "gcm": "GCM",
        "montserrat": "MNI",
        "mni": "MNI",
        "turks and caicos islands": "PLS",
        "turks and caicos": "PLS",
        "pls": "PLS",
        "guadeloupe": "PTP",
        "ptp": "PTP",
        "martinique": "FDF",
        "fdf": "FDF",
        "saint barthelemy": "SBH",
        "st barthelemy": "SBH",
        "st barths": "SBH",
        "sbh": "SBH",
        "saint martin": "SFG",
        "st martin": "SFG",
        "sfg": "SFG",
        "aruba": "AUA",
        "aua": "AUA",
        "curacao": "CUR",
        "curaçao": "CUR",
        "cur": "CUR",
        "sint maarten": "SXM",
        "sxm": "SXM",
        "bonaire": "BON",
        "bon": "BON",
        "sint eustatius": "EUX",
        "eux": "EUX",
        "saba": "SAB",
        "sab": "SAB",
        "puerto rico": "SJU",
        "san juan": "SJU",
        "sju": "SJU",
        "u.s. virgin islands": "STT",
        "us virgin islands": "STT",
        "united states virgin islands": "STT",
        "stt": "STT",
    }

    cleaned = place.strip().lower()

    return aliases.get(
        cleaned,
        place.strip().upper()
    )


def recommend_destinations_tool(
    days,
    preferences=None,
    origin="POS",
    travel_date=None,
    budget=None
):
    """
    Returns ranked Caribbean destination recommendations.

    Budget is currently stored as context only because real trip pricing
    has not been connected yet.
    """
    origin_code = _normalize_place(origin)

    results = _recommend_destinations(
        days=days,
        preferences=preferences or {},
        origin=origin_code,
        travel_date=travel_date,
        budget=budget,
    )

    if not results:
        return {
            "status": "no_matches",
            "results": []
        }

    return {
        "status": "ok",
        "origin": origin_code,
        "days": days,
        "budget": budget,
        "budget_evaluated": False,
        "travel_date": travel_date,
        "results": results
    }


def get_destination_details_tool(name):
    """Looks up one supported Caribbean destination."""
    destinations = load_destinations()

    cleaned_name = name.strip().lower()

    for destination in destinations:
        if (
            destination["name"].lower()
            == cleaned_name
            or destination["country"].lower()
            == cleaned_name
        ):
            return {
                "status": "ok",
                "destination": destination
            }

    return {
        "status": "not_found",
        "message": (
            f"No destination named '{name}' "
            "in the current Caribbean catalog."
        ),
        "available_destinations": [
            destination["name"]
            for destination in destinations
        ],
    }


def check_route_tool(origin, destination):
    """Checks the current seeded route dataset."""
    routes = load_routes()

    origin_code = _normalize_place(origin)
    destination_code = _normalize_place(destination)

    route = find_route(
        origin_code,
        destination_code,
        routes
    )

    if route["route_type"] == "unknown":
        return {
            "status": "unknown",
            "origin": origin_code,
            "destination": destination_code,
            "route_type": "unknown",
            "message": (
                "This route is not covered by the current "
                "seeded route dataset yet."
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
    Gets real near-term weather directly from WeatherAPI.com.

    Weather is not restricted to destinations.json at the API level, but
    WeyWeGoing? is designed around the Caribbean catalog.
    """
    try:
        weather_data = get_forecast(
            destination,
            days
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }

    return {
        "status": "ok",
        "destination": destination,
        "data_type": "live_forecast",
        "location": weather_data["location"],
        "forecast": weather_data["forecast"],
    }


def convert_currency_tool(
    amount,
    from_currency,
    to_currency
):
    """Converts money using the current seeded demo exchange rates."""
    currency_data = load_currency()
    rates_to_ttd = currency_data["rates_to_ttd"]

    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": (
                f"No seeded rate for {from_code}. "
                "Currency coverage will expand when a live FX API is added."
            ),
        }

    if to_code not in rates_to_ttd:
        return {
            "status": "not_found",
            "message": (
                f"No seeded rate for {to_code}. "
                "Currency coverage will expand when a live FX API is added."
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
                "Rank supported Caribbean destinations using user "
                "preferences, route convenience when known, and real "
                "near-term weather when an exact date is available. "
                "Budget may be passed as context but is not evaluated "
                "until real pricing data is connected."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Length of trip in days.",
                    },
                    "budget": {
                        "type": "number",
                        "description": (
                            "Optional total trip budget in TTD. "
                            "Currently retained as context only."
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
                            "Exact trip start date in YYYY-MM-DD. "
                            "Only include when the user gives an exact date."
                        ),
                    },
                    "preferences": {
                        "type": "object",
                        "description": (
                            "Only include interests the user actually "
                            "expressed, with weights from 0.0 to 1.0."
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
                "required": ["days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_destination_details",
            "description": (
                "Get the stored metadata and preference scores for one "
                "supported Caribbean destination."
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
                "Check whether the current seeded route dataset contains "
                "a direct or one-stop route between two Caribbean places."
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
                "Get the real near-term weather forecast for a Caribbean "
                "location using WeatherAPI.com."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "destination": {
                        "type": "string",
                        "description": "Caribbean destination or city name.",
                    },
                    "days": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 3,
                        "description": "Number of forecast days, 1 to 3.",
                    },
                },
                "required": ["destination"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "convert_currency",
            "description": (
                "Convert money using the current seeded currency rates."
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
