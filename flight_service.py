"""
flight_service.py

Flight search for WeyWeGoing?.

Two modes, and the caller always knows which one it got via
`data_type` in the returned dict:

- "sandbox_quote": real calls to the Amadeus Self-Service Flight Offers
  Search API, TEST environment. Amadeus documents its test environment as
  a limited, cached sample data set for development - it is NOT
  production/live pricing, so this is labeled "sandbox", never "live".
  Needs a free developer account (see config.FLIGHTS_SETUP_MESSAGE).
- "demo_estimate": used automatically when no Amadeus credentials are
  configured, so the app still demos end to end. This is a rough,
  deterministic placeholder number, clearly labeled as not a real fare.

Either way this module never claims a fare is a live production price.
"""

import hashlib
import time
from datetime import datetime, timezone

import requests

import config
from currency_service import convert_currency

AUTH_URL = "https://test.api.amadeus.com/v1/security/oauth2/token"
SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

_token_cache = {"access_token": None, "expires_at": 0}


class FlightSearchError(Exception):
    """Raised for provider-side failures with a user-facing message."""


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get_access_token():
    now = time.time()

    if (
        _token_cache["access_token"]
        and now < _token_cache["expires_at"] - 30
    ):
        return _token_cache["access_token"]

    response = requests.post(
        AUTH_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": config.AMADEUS_CLIENT_ID,
            "client_secret": config.AMADEUS_CLIENT_SECRET,
        },
        timeout=10,
    )

    if response.status_code == 401:
        raise FlightSearchError(
            "Amadeus rejected the configured API credentials. Double "
            "check AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET in .env."
        )

    response.raise_for_status()

    data = response.json()

    _token_cache["access_token"] = data["access_token"]
    _token_cache["expires_at"] = now + data.get("expires_in", 1700)

    return _token_cache["access_token"]


def _extract_amadeus_error(response):
    try:
        data = response.json()
        errors = data.get("errors", [])

        if errors:
            return "; ".join(
                f"{error.get('title', 'Error')}: {error.get('detail', '')}"
                .strip(": ")
                for error in errors
            )
    except ValueError:
        pass

    return response.text[:300]


def _summarize_itinerary(itinerary):
    segments = itinerary.get("segments", [])

    if not segments:
        return None

    return {
        "origin": segments[0]["departure"]["iataCode"],
        "destination": segments[-1]["arrival"]["iataCode"],
        "departure_time": segments[0]["departure"]["at"],
        "arrival_time": segments[-1]["arrival"]["at"],
        "stops": len(segments) - 1,
        "duration": itinerary.get("duration"),
        "carriers": sorted({
            segment["carrierCode"] for segment in segments
        }),
    }


def _normalize_offer(offer):
    price = offer.get("price", {})

    itineraries = [
        summary
        for summary in (
            _summarize_itinerary(itinerary)
            for itinerary in offer.get("itineraries", [])
        )
        if summary
    ]

    return {
        "price_total": float(
            price.get("grandTotal", price.get("total", 0))
        ),
        "currency": price.get("currency"),
        "validating_airlines": offer.get("validatingAirlineCodes", []),
        "bookable_seats": offer.get("numberOfBookableSeats"),
        "itineraries": itineraries,
    }


def _search_live(
    origin,
    destination,
    depart_date,
    return_date,
    travelers,
    currency
):
    token = _get_access_token()

    params = {
        "originLocationCode": origin,
        "destinationLocationCode": destination,
        "departureDate": depart_date,
        "adults": travelers,
        "currencyCode": currency,
        "max": 5,
    }

    if return_date:
        params["returnDate"] = return_date

    try:
        response = requests.get(
            SEARCH_URL,
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
    except requests.exceptions.Timeout:
        raise FlightSearchError(
            "Flight search timed out contacting Amadeus. Try again."
        )
    except requests.exceptions.ConnectionError:
        raise FlightSearchError(
            "Could not reach the Amadeus flight search API "
            "(network error)."
        )

    if response.status_code == 400:
        raise FlightSearchError(
            "Amadeus rejected this search "
            f"({_extract_amadeus_error(response)}). This can mean the "
            "route/airport codes aren't supported in the test "
            "environment, or a date is invalid."
        )

    if response.status_code == 401:
        raise FlightSearchError(
            "Amadeus authentication failed. Check your API credentials."
        )

    if response.status_code == 429:
        raise FlightSearchError(
            "Amadeus rate limit reached for the test environment. "
            "Wait a moment and try again."
        )

    if response.status_code >= 400:
        raise FlightSearchError(
            f"Amadeus returned an error: {_extract_amadeus_error(response)}"
        )

    data = response.json()

    return [_normalize_offer(offer) for offer in data.get("data", [])]


def _demo_price_usd(origin, destination, round_trip):
    """
    Deterministic (not random) placeholder fare so demo mode is
    reproducible and testable. This is explicitly NOT a real fare.
    """
    digest = hashlib.sha256(
        f"{origin}-{destination}".encode()
    ).hexdigest()

    base = 140 + (int(digest[:4], 16) % 260)  # 140-400 USD, one-way

    if round_trip:
        base = round(base * 1.75)

    return base


def _demo_quote(
    origin,
    destination,
    depart_date,
    return_date,
    travelers,
    currency,
    retrieved_at
):
    per_traveler_usd = _demo_price_usd(
        origin,
        destination,
        bool(return_date),
    )

    total_usd = per_traveler_usd * max(travelers, 1)

    total = total_usd
    resolved_currency = "USD"

    if currency.upper() != "USD":
        try:
            converted = convert_currency(total_usd, "USD", currency)
            total = converted["converted_amount"]
            resolved_currency = converted["to_currency"]
        except Exception:
            # Currency conversion failing shouldn't break demo mode -
            # fall back to the USD estimate and say so.
            total = total_usd
            resolved_currency = "USD"

    return {
        "status": "ok",
        "data_type": "demo_estimate",
        "source": (
            "DEMO ESTIMATE - not a real fare. No flight provider "
            "credentials are configured."
        ),
        "retrieved_at": retrieved_at,
        "origin": origin,
        "destination": destination,
        "depart_date": depart_date,
        "return_date": return_date,
        "travelers": travelers,
        "currency": resolved_currency,
        "price_total": round(total, 2),
        "offers": [],
        "disclaimer": (
            "This is a rough, non-live placeholder for demo purposes "
            "only, not a bookable price. Configure AMADEUS_CLIENT_ID / "
            "AMADEUS_CLIENT_SECRET for real sandbox flight quotes."
        ),
    }


def search_flights(
    origin,
    destination,
    depart_date,
    return_date=None,
    travelers=1,
    currency="USD"
):
    """
    Searches flights and always labels the result's provenance.

    Returns a dict with status one of:
      "ok"              - offers/estimate present, see data_type
      "no_results"       - provider reached, no matching offers
      "error"            - provider call failed (see message)
    """
    retrieved_at = _now_iso()
    currency = (currency or "USD").upper()

    if not config.FLIGHTS_CONFIGURED:
        return _demo_quote(
            origin,
            destination,
            depart_date,
            return_date,
            travelers,
            currency,
            retrieved_at,
        )

    try:
        offers = _search_live(
            origin,
            destination,
            depart_date,
            return_date,
            travelers,
            currency,
        )
    except FlightSearchError as error:
        return {
            "status": "error",
            "data_type": "sandbox_quote",
            "message": str(error),
            "retrieved_at": retrieved_at,
        }
    except requests.exceptions.RequestException as error:
        return {
            "status": "error",
            "data_type": "sandbox_quote",
            "message": f"Flight search request failed: {error}",
            "retrieved_at": retrieved_at,
        }

    if not offers:
        return {
            "status": "no_results",
            "data_type": "sandbox_quote",
            "message": (
                "No flight offers found for this route and date in the "
                "Amadeus test environment. The test environment has "
                "limited sample inventory, so this does not necessarily "
                "mean the real route doesn't exist."
            ),
            "retrieved_at": retrieved_at,
        }

    cheapest = min(offers, key=lambda offer: offer["price_total"])

    return {
        "status": "ok",
        "data_type": "sandbox_quote",
        "source": (
            "Amadeus Self-Service Flight Offers Search (TEST "
            "environment - sample inventory, not production live "
            "pricing)"
        ),
        "retrieved_at": retrieved_at,
        "origin": origin,
        "destination": destination,
        "depart_date": depart_date,
        "return_date": return_date,
        "travelers": travelers,
        "currency": cheapest["currency"] or currency,
        "price_total": cheapest["price_total"],
        "offers": offers,
    }
