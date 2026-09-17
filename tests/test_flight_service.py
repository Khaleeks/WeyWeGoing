from unittest.mock import Mock, patch

import pytest
import requests

import flight_service


@pytest.fixture(autouse=True)
def reset_token_cache():
    flight_service._token_cache["access_token"] = None
    flight_service._token_cache["expires_at"] = 0
    yield
    flight_service._token_cache["access_token"] = None
    flight_service._token_cache["expires_at"] = 0


def test_demo_mode_when_not_configured():
    with patch("flight_service.config.FLIGHTS_CONFIGURED", False):
        result = flight_service.search_flights(
            origin="POS",
            destination="BGI",
            depart_date="2026-12-01",
            travelers=2,
            currency="USD",
        )

    assert result["status"] == "ok"
    assert result["data_type"] == "demo_estimate"
    assert "DEMO" in result["source"]
    assert result["price_total"] > 0


def test_demo_mode_is_deterministic_for_same_route():
    with patch("flight_service.config.FLIGHTS_CONFIGURED", False):
        first = flight_service.search_flights("POS", "BGI", "2026-12-01")
        second = flight_service.search_flights("POS", "BGI", "2026-12-01")

    assert first["price_total"] == second["price_total"]


def _fake_offer():
    return {
        "price": {"grandTotal": "250.50", "currency": "USD"},
        "validatingAirlineCodes": ["BW"],
        "numberOfBookableSeats": 4,
        "itineraries": [{
            "duration": "PT2H10M",
            "segments": [{
                "departure": {"iataCode": "POS", "at": "2026-12-01T08:00:00"},
                "arrival": {"iataCode": "BGI", "at": "2026-12-01T09:10:00"},
                "carrierCode": "BW",
            }],
        }],
    }


def test_live_search_parses_offers():
    token_response = Mock(status_code=200)
    token_response.json.return_value = {
        "access_token": "fake-token",
        "expires_in": 1700,
    }

    search_response = Mock(status_code=200)
    search_response.json.return_value = {"data": [_fake_offer()]}

    with patch("flight_service.config.FLIGHTS_CONFIGURED", True), \
         patch("flight_service.config.AMADEUS_CLIENT_ID", "id"), \
         patch("flight_service.config.AMADEUS_CLIENT_SECRET", "secret"), \
         patch(
             "flight_service.requests.post", return_value=token_response
         ), \
         patch(
             "flight_service.requests.get", return_value=search_response
         ):
        result = flight_service.search_flights(
            origin="POS", destination="BGI", depart_date="2026-12-01"
        )

    assert result["status"] == "ok"
    assert result["data_type"] == "sandbox_quote"
    assert result["price_total"] == 250.50
    assert result["offers"][0]["validating_airlines"] == ["BW"]


def test_live_search_no_results():
    token_response = Mock(status_code=200)
    token_response.json.return_value = {
        "access_token": "fake-token", "expires_in": 1700
    }
    search_response = Mock(status_code=200)
    search_response.json.return_value = {"data": []}

    with patch("flight_service.config.FLIGHTS_CONFIGURED", True), \
         patch("flight_service.config.AMADEUS_CLIENT_ID", "id"), \
         patch("flight_service.config.AMADEUS_CLIENT_SECRET", "secret"), \
         patch(
             "flight_service.requests.post", return_value=token_response
         ), \
         patch(
             "flight_service.requests.get", return_value=search_response
         ):
        result = flight_service.search_flights(
            origin="POS", destination="ZZZ", depart_date="2026-12-01"
        )

    assert result["status"] == "no_results"


def test_live_search_handles_timeout():
    token_response = Mock(status_code=200)
    token_response.json.return_value = {
        "access_token": "fake-token", "expires_in": 1700
    }

    with patch("flight_service.config.FLIGHTS_CONFIGURED", True), \
         patch("flight_service.config.AMADEUS_CLIENT_ID", "id"), \
         patch("flight_service.config.AMADEUS_CLIENT_SECRET", "secret"), \
         patch(
             "flight_service.requests.post", return_value=token_response
         ), \
         patch(
             "flight_service.requests.get",
             side_effect=requests.exceptions.Timeout,
         ):
        result = flight_service.search_flights(
            origin="POS", destination="BGI", depart_date="2026-12-01"
        )

    assert result["status"] == "error"
    assert "timed out" in result["message"]


def test_live_search_handles_400_as_unsupported_route():
    token_response = Mock(status_code=200)
    token_response.json.return_value = {
        "access_token": "fake-token", "expires_in": 1700
    }
    error_response = Mock(status_code=400)
    error_response.json.return_value = {
        "errors": [{"title": "INVALID FORMAT", "detail": "bad code"}]
    }
    error_response.text = "bad request"

    with patch("flight_service.config.FLIGHTS_CONFIGURED", True), \
         patch("flight_service.config.AMADEUS_CLIENT_ID", "id"), \
         patch("flight_service.config.AMADEUS_CLIENT_SECRET", "secret"), \
         patch(
             "flight_service.requests.post", return_value=token_response
         ), \
         patch(
             "flight_service.requests.get", return_value=error_response
         ):
        result = flight_service.search_flights(
            origin="XXX", destination="YYY", depart_date="2026-12-01"
        )

    assert result["status"] == "error"
    assert "INVALID FORMAT" in result["message"]


def test_auth_failure_produces_clear_message():
    auth_response = Mock(status_code=401)

    with patch("flight_service.config.FLIGHTS_CONFIGURED", True), \
         patch("flight_service.config.AMADEUS_CLIENT_ID", "bad"), \
         patch("flight_service.config.AMADEUS_CLIENT_SECRET", "bad"), \
         patch(
             "flight_service.requests.post", return_value=auth_response
         ):
        result = flight_service.search_flights(
            origin="POS", destination="BGI", depart_date="2026-12-01"
        )

    assert result["status"] == "error"
    assert "credentials" in result["message"]
