"""
request_schema.py

Deterministic validation for a trip request.

The LLM extracts values from natural language and calls a tool with them.
This module decides whether that extraction is complete and sane enough to
act on. It never invents missing values - it reports exactly what is
missing or invalid so the agent can ask the user a follow-up question.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

VALID_BUDGET_SCOPES = ("per_person", "group")

MAX_TRAVELERS = 20
MAX_DURATION_DAYS = 60
MAX_LOOKAHEAD_DAYS = 330  # matches typical flight-search booking horizons


@dataclass
class TripRequest:
    origin: str
    days: int
    preferences: dict = field(default_factory=dict)
    travel_date: str | None = None
    return_date: str | None = None
    travelers: int = 1
    budget_amount: float | None = None
    budget_currency: str = "USD"
    budget_scope: str | None = None


def _parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def validate_trip_request(
    origin=None,
    days=None,
    preferences=None,
    travel_date=None,
    return_date=None,
    travelers=1,
    budget_amount=None,
    budget_currency="USD",
    budget_scope=None,
):
    """
    Validates a trip request.

    Returns (request_or_none, missing_fields, errors).

    - missing_fields: essential information the user has not given yet.
      The agent should ask about these instead of guessing.
    - errors: values that were supplied but are invalid (e.g. negative
      travelers, a travel date in the past).
    """
    missing_fields = []
    errors = []

    if not origin or not str(origin).strip():
        missing_fields.append({
            "field": "origin",
            "question": (
                "Where are you departing from? (a city, airport, or "
                "Caribbean island)"
            ),
        })

    if not days:
        missing_fields.append({
            "field": "days",
            "question": (
                "How many days is the trip, or what are your travel dates?"
            ),
        })
    elif not isinstance(days, int) or days <= 0:
        errors.append("days must be a positive whole number.")
    elif days > MAX_DURATION_DAYS:
        errors.append(
            f"days must be {MAX_DURATION_DAYS} or fewer for this prototype."
        )

    if travelers is None:
        travelers = 1

    if not isinstance(travelers, int) or travelers <= 0:
        errors.append("travelers must be a positive whole number.")
    elif travelers > MAX_TRAVELERS:
        errors.append(
            f"travelers must be {MAX_TRAVELERS} or fewer for this prototype."
        )

    parsed_travel_date = None

    if travel_date:
        parsed_travel_date = _parse_date(travel_date)

        if parsed_travel_date is None:
            errors.append(
                "travel_date must be in YYYY-MM-DD format."
            )
        elif parsed_travel_date < date.today():
            errors.append("travel_date cannot be in the past.")
        elif parsed_travel_date > date.today() + timedelta(
            days=MAX_LOOKAHEAD_DAYS
        ):
            errors.append(
                "travel_date is too far in the future for flight quotes "
                f"({MAX_LOOKAHEAD_DAYS} days max)."
            )

    parsed_return_date = None

    if return_date:
        parsed_return_date = _parse_date(return_date)

        if parsed_return_date is None:
            errors.append("return_date must be in YYYY-MM-DD format.")
        elif (
            parsed_travel_date
            and parsed_return_date < parsed_travel_date
        ):
            errors.append("return_date cannot be before travel_date.")

    if budget_amount is not None:
        if not isinstance(budget_amount, (int, float)) or budget_amount <= 0:
            errors.append("budget_amount must be a positive number.")

        if not budget_scope:
            missing_fields.append({
                "field": "budget_scope",
                "question": (
                    "Is that budget per person, or for the whole group?"
                ),
            })
        elif budget_scope not in VALID_BUDGET_SCOPES:
            errors.append(
                "budget_scope must be 'per_person' or 'group'."
            )

    if missing_fields or errors:
        return None, missing_fields, errors

    request = TripRequest(
        origin=str(origin).strip(),
        days=int(days),
        preferences=preferences or {},
        travel_date=travel_date,
        return_date=return_date,
        travelers=int(travelers),
        budget_amount=budget_amount,
        budget_currency=(budget_currency or "USD").upper(),
        budget_scope=budget_scope,
    )

    return request, [], []
