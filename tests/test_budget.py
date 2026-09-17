from unittest.mock import patch

from budget import evaluate_flight_budget


def test_same_currency_group_budget_no_conversion_needed():
    with patch("budget.convert_currency") as mock_convert:
        result = evaluate_flight_budget(
            budget_amount=1000,
            budget_currency="USD",
            budget_scope="group",
            travelers=2,
            flight_price_total=900,
            flight_currency="USD",
        )

        mock_convert.assert_not_called()
        assert result["within_budget_for_flights_only"] is True
        assert result["flight_total_group"] == 900
        assert result["flight_total_per_person"] == 450
        assert result["remaining_after_flights"] == 100


def test_per_person_scope_compares_divided_cost():
    result = evaluate_flight_budget(
        budget_amount=300,
        budget_currency="USD",
        budget_scope="per_person",
        travelers=2,
        flight_price_total=900,
        flight_currency="USD",
    )

    # 900 / 2 = 450 per person > 300 budget
    assert result["flight_total_per_person"] == 450
    assert result["within_budget_for_flights_only"] is False
    assert result["remaining_after_flights"] == -150


def test_converts_currency_when_flight_currency_differs():
    fake_conversion = {
        "converted_amount": 1800.0,
        "rate": 2.0,
        "date": "2026-01-01",
    }

    with patch(
        "budget.convert_currency", return_value=fake_conversion
    ) as mock_convert:
        result = evaluate_flight_budget(
            budget_amount=2000,
            budget_currency="TTD",
            budget_scope="group",
            travelers=1,
            flight_price_total=900,
            flight_currency="USD",
        )

        mock_convert.assert_called_once_with(900, "USD", "TTD")
        assert result["flight_total_group"] == 1800.0
        assert result["within_budget_for_flights_only"] is True


def test_never_omits_excluded_expenses_disclaimer():
    result = evaluate_flight_budget(
        budget_amount=500,
        budget_currency="USD",
        budget_scope="group",
        travelers=1,
        flight_price_total=100,
        flight_currency="USD",
    )

    assert "accommodation" in result["excluded_expenses"]
    assert "disclaimer" in result
    assert "whole trip" in result["disclaimer"] or "trip" in result["disclaimer"]
