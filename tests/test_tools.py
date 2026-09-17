from unittest.mock import patch

import tools


def test_recommend_destinations_missing_origin_does_not_call_planner():
    with patch("tools._recommend_destinations") as mock_recommend:
        result = tools.recommend_destinations_tool(days=5, origin=None)

        mock_recommend.assert_not_called()
        assert result["status"] == "missing_info"
        assert result["missing_fields"][0]["field"] == "origin"


def test_recommend_destinations_budget_without_scope_is_missing_info():
    with patch("tools._recommend_destinations") as mock_recommend:
        result = tools.recommend_destinations_tool(
            days=5, origin="POS", budget_amount=500
        )

        mock_recommend.assert_not_called()
        assert result["status"] == "missing_info"
        assert any(
            field["field"] == "budget_scope"
            for field in result["missing_fields"]
        )


def test_recommend_destinations_invalid_travelers():
    result = tools.recommend_destinations_tool(
        days=5, origin="POS", travelers=0
    )

    assert result["status"] == "invalid_request"


def test_recommend_destinations_without_travel_date_skips_flight_lookup():
    fake_destination = {
        "name": "Fakeland",
        "country": "Fakeland",
        "country_code": "FK",
        "region_type": "Independent Nation",
        "airport": "FKL",
        "currency": "FKD",
        "score_breakdown": {"final_score": 80},
        "route": {"route_type": "unknown", "legs": []},
        "weather": None,
        "travel_date": None,
    }

    with patch(
        "tools._recommend_destinations", return_value=[fake_destination]
    ), patch("tools.search_flights") as mock_search_flights:
        result = tools.recommend_destinations_tool(
            days=5, origin="POS"
        )

        mock_search_flights.assert_not_called()
        assert result["status"] == "ok"
        assert result["results"][0]["flight"] is None
        assert result["results"][0]["budget_evaluation"] is None


def test_recommend_destinations_with_travel_date_attaches_flight_and_budget():
    fake_destination = {
        "name": "Fakeland",
        "country": "Fakeland",
        "country_code": "FK",
        "region_type": "Independent Nation",
        "airport": "FKL",
        "currency": "FKD",
        "score_breakdown": {"final_score": 80},
        "route": {"route_type": "unknown", "legs": []},
        "weather": None,
        "travel_date": "2026-12-01",
    }

    fake_flight_quote = {
        "status": "ok",
        "data_type": "demo_estimate",
        "price_total": 400,
        "currency": "USD",
        "retrieved_at": "2026-01-01T00:00:00Z",
        "travelers": 1,
    }

    with patch(
        "tools._recommend_destinations", return_value=[fake_destination]
    ), patch(
        "tools.search_flights", return_value=fake_flight_quote
    ) as mock_search_flights:
        result = tools.recommend_destinations_tool(
            days=5,
            origin="POS",
            travel_date="2026-12-01",
            budget_amount=1000,
            budget_currency="USD",
            budget_scope="group",
        )

        mock_search_flights.assert_called_once()
        assert result["results"][0]["flight"] == fake_flight_quote
        assert result["results"][0]["budget_evaluation"][
            "within_budget_for_flights_only"
        ] is True


def test_get_flight_quote_tool_normalizes_place_names():
    with patch("tools.search_flights") as mock_search_flights:
        mock_search_flights.return_value = {"status": "ok"}

        tools.get_flight_quote_tool(
            origin="trinidad",
            destination="barbados",
            depart_date="2026-12-01",
        )

        mock_search_flights.assert_called_once_with(
            origin="POS",
            destination="BGI",
            depart_date="2026-12-01",
            return_date=None,
            travelers=1,
            currency="USD",
        )
