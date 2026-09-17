"""
tools.py

Defines the tools WeyWeGoing?'s LLM can choose to call. Each tool
function validates its own inputs and delegates all arithmetic to
deterministic modules (request_schema, planner/scoring, flight_service,
budget, currency_service) - the LLM only ever sees already-computed
results to narrate.

destinations.json is the Caribbean destination catalog (seeded).
routes.json is seeded route coverage, still incomplete.
Weather and currency conversion are live. Flights are a live Amadeus
sandbox quote, or a clearly-labeled demo estimate without credentials.
"""

from airports import normalize_place as _normalize_place
from budget import evaluate_flight_budget
from flight_service import search_flights
from planner import (
    load_destinations,
    load_routes,
    find_route,
    recommend_destinations as _recommend_destinations
)
from request_schema import validate_trip_request
from weather_service import get_forecast

from currency_service import (
    convert_currency
)


def _add_days(date_string, days):
    from datetime import datetime, timedelta

    parsed = datetime.strptime(date_string, "%Y-%m-%d")

    return (parsed + timedelta(days=days)).strftime("%Y-%m-%d")


def _attach_flight_and_budget(result, request):
    """
    For one ranked destination, fetches a flight quote (sandbox or demo)
    and, if the user gave a budget, evaluates it deterministically.

    This never changes the destination's ranking - preference/route/
    weather scoring already decided the order. It only adds cost
    transparency to results that are already being shown.
    """
    if not request.travel_date:
        result["flight"] = None
        result["budget_evaluation"] = None
        return result

    return_date = request.return_date

    if not return_date and request.days:
        return_date = _add_days(request.travel_date, request.days)

    flight_quote = search_flights(
        origin=request.origin,
        destination=result["airport"],
        depart_date=request.travel_date,
        return_date=return_date,
        travelers=request.travelers,
        currency=request.budget_currency,
    )

    result["flight"] = flight_quote

    if (
        request.budget_amount is not None
        and flight_quote.get("status") == "ok"
    ):
        result["budget_evaluation"] = evaluate_flight_budget(
            budget_amount=request.budget_amount,
            budget_currency=request.budget_currency,
            budget_scope=request.budget_scope,
            travelers=request.travelers,
            flight_price_total=flight_quote["price_total"],
            flight_currency=flight_quote["currency"],
        )
    else:
        result["budget_evaluation"] = None

    return result


def recommend_destinations_tool(
    days=None,
    preferences=None,
    origin=None,
    travel_date=None,
    return_date=None,
    travelers=1,
    budget_amount=None,
    budget_currency="USD",
    budget_scope=None
):
    """
    Returns ranked Caribbean destination recommendations, with a flight
    quote and budget check attached to each when a travel date is given.

    If essential information is missing or a supplied value is invalid,
    returns status "missing_info" or "invalid_request" instead of
    guessing - the agent should ask the user rather than assume.
    """
    request, missing_fields, errors = validate_trip_request(
        origin=origin,
        days=days,
        preferences=preferences,
        travel_date=travel_date,
        return_date=return_date,
        travelers=travelers,
        budget_amount=budget_amount,
        budget_currency=budget_currency,
        budget_scope=budget_scope,
    )

    if errors:
        return {
            "status": "invalid_request",
            "errors": errors,
        }

    if missing_fields:
        return {
            "status": "missing_info",
            "missing_fields": missing_fields,
        }

    origin_code = _normalize_place(request.origin)
    request.origin = origin_code

    results = _recommend_destinations(
        days=request.days,
        preferences=request.preferences,
        origin=origin_code,
        travel_date=request.travel_date,
        budget=request.budget_amount,
    )

    if not results:
        return {
            "status": "no_matches",
            "results": []
        }

    results = [
        _attach_flight_and_budget(result, request)
        for result in results
    ]

    return {
        "status": "ok",
        "origin": origin_code,
        "days": request.days,
        "travelers": request.travelers,
        "budget_amount": request.budget_amount,
        "budget_currency": request.budget_currency,
        "budget_scope": request.budget_scope,
        "travel_date": request.travel_date,
        "results": results,
    }


def get_flight_quote_tool(
    origin,
    destination,
    depart_date,
    return_date=None,
    travelers=1,
    currency="USD"
):
    """
    Fetches a single flight quote directly, without going through
    destination recommendations. Useful when the user just wants a
    price for a specific route/date.
    """
    origin_code = _normalize_place(origin)
    destination_code = _normalize_place(destination)

    return search_flights(
        origin=origin_code,
        destination=destination_code,
        depart_date=depart_date,
        return_date=return_date,
        travelers=travelers,
        currency=currency,
    )


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
    """
    Converts money using live Frankfurter exchange rates.
    """

    try:
        result = convert_currency(
            amount,
            from_currency,
            to_currency
        )

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }

    return {
        "status": "ok",
        "amount": result["amount"],
        "from_currency": (
            result["from_currency"]
        ),
        "to_currency": (
            result["to_currency"]
        ),
        "rate": result["rate"],
        "converted_amount": (
            result["converted_amount"]
        ),
        "rate_date": result["date"],
        "data_type": "live_exchange_rate",
    }


TOOL_FUNCTIONS = {
    "recommend_destinations": recommend_destinations_tool,
    "get_destination_details": get_destination_details_tool,
    "check_route": check_route_tool,
    "get_weather": get_weather_tool,
    "convert_currency": convert_currency_tool,
    "get_flight_quote": get_flight_quote_tool,
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
                "When a travel_date is given, also attaches a flight "
                "quote (sandbox or clearly-labeled demo estimate) and a "
                "flights-only budget check to each result. Returns "
                "status 'missing_info' if essential fields (origin, "
                "trip length, or whether a stated budget is per-person "
                "or for the group) are missing - ask the user instead "
                "of guessing them."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {
                        "type": "integer",
                        "description": "Length of trip in days.",
                    },
                    "origin": {
                        "type": "string",
                        "description": (
                            "Starting place or airport code. Do not "
                            "invent one - ask the user if not given."
                        ),
                    },
                    "travel_date": {
                        "type": "string",
                        "description": (
                            "Exact trip start date in YYYY-MM-DD. "
                            "Only include when the user gives an exact "
                            "date - do not invent one from a vague month."
                        ),
                    },
                    "return_date": {
                        "type": "string",
                        "description": (
                            "Exact return date in YYYY-MM-DD, if the "
                            "user gave one. Otherwise omit it and it "
                            "will be computed from travel_date + days."
                        ),
                    },
                    "travelers": {
                        "type": "integer",
                        "description": (
                            "Number of travelers. Defaults to 1 if the "
                            "user doesn't say."
                        ),
                    },
                    "budget_amount": {
                        "type": "number",
                        "description": (
                            "Optional total budget the user stated, as "
                            "a plain number."
                        ),
                    },
                    "budget_currency": {
                        "type": "string",
                        "description": (
                            "Currency code for budget_amount, e.g. USD, "
                            "TTD. Ask if the user gives a budget without "
                            "a currency and it isn't obvious."
                        ),
                    },
                    "budget_scope": {
                        "type": "string",
                        "enum": ["per_person", "group"],
                        "description": (
                            "Whether budget_amount is per traveler or "
                            "for the whole group. Required whenever "
                            "budget_amount is given - ask the user if "
                            "they didn't say."
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
                "required": ["days", "origin"],
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
                "Convert money between currencies using live Frankfurter exchange rates."
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
    {
        "type": "function",
        "function": {
            "name": "get_flight_quote",
            "description": (
                "Get a flight price quote for one specific origin, "
                "destination, and exact date, without ranking "
                "destinations. Returns a sandbox quote (Amadeus test "
                "environment) if flight credentials are configured, "
                "otherwise a clearly-labeled demo estimate. Never a "
                "live production price."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "origin": {
                        "type": "string",
                        "description": "Departure place or airport code.",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination place or airport code.",
                    },
                    "depart_date": {
                        "type": "string",
                        "description": "Departure date in YYYY-MM-DD.",
                    },
                    "return_date": {
                        "type": "string",
                        "description": (
                            "Return date in YYYY-MM-DD, for round trips."
                        ),
                    },
                    "travelers": {
                        "type": "integer",
                        "description": "Number of travelers. Default 1.",
                    },
                    "currency": {
                        "type": "string",
                        "description": "Currency code for the price.",
                    },
                },
                "required": [
                    "origin",
                    "destination",
                    "depart_date"
                ],
            },
        },
    },
]
