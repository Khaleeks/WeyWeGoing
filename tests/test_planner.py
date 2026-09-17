from unittest.mock import patch

from planner import find_route, recommend_destinations

FAKE_DESTINATIONS = [
    {
        "name": "Beachville",
        "country": "Beachville",
        "country_code": "BV",
        "airport": "BEA",
        "currency": "USD",
        "region_type": "Independent Nation",
        "scores": {"beach": 10, "nightlife": 2},
    },
    {
        "name": "Party Island",
        "country": "Party Island",
        "country_code": "PI",
        "airport": "PAR",
        "currency": "USD",
        "region_type": "Independent Nation",
        "scores": {"beach": 2, "nightlife": 10},
    },
]

FAKE_ROUTES = [
    {
        "origin": "POS",
        "destination": "BEA",
        "airline": "Test Air",
        "direct": True,
        "estimated_duration_minutes": 30,
        "frequency": "daily",
    },
]


def test_find_route_direct_and_unknown():
    direct = find_route("POS", "BEA", FAKE_ROUTES)
    assert direct["route_type"] == "direct"

    unknown = find_route("POS", "PAR", FAKE_ROUTES)
    assert unknown["route_type"] == "unknown"


def test_recommend_destinations_ranks_by_preference_match():
    with patch(
        "planner.load_destinations", return_value=FAKE_DESTINATIONS
    ), patch("planner.load_routes", return_value=FAKE_ROUTES):
        results = recommend_destinations(
            days=5,
            preferences={"beach": 1.0},
            origin="POS",
        )

    assert results[0]["name"] == "Beachville"
    assert results[0]["route"]["route_type"] == "direct"
    assert results[1]["route"]["route_type"] == "unknown"


def test_recommend_destinations_excludes_origin_airport():
    with patch(
        "planner.load_destinations", return_value=FAKE_DESTINATIONS
    ), patch("planner.load_routes", return_value=FAKE_ROUTES):
        results = recommend_destinations(
            days=5,
            preferences={},
            origin="BEA",
        )

    names = [result["name"] for result in results]
    assert "Beachville" not in names


def test_recommend_destinations_skips_weather_on_failure():
    with patch(
        "planner.load_destinations", return_value=FAKE_DESTINATIONS
    ), patch("planner.load_routes", return_value=FAKE_ROUTES), patch(
        "planner.get_weather_for_date", side_effect=RuntimeError("boom")
    ):
        results = recommend_destinations(
            days=5,
            preferences={},
            origin="POS",
            travel_date="2026-12-01",
        )

    assert all(result["weather"] is None for result in results)
