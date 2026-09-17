from request_schema import validate_trip_request


def test_missing_origin_and_days_are_reported():
    request, missing, errors = validate_trip_request(
        origin=None, days=None
    )

    assert request is None
    assert errors == []
    fields = {item["field"] for item in missing}
    assert fields == {"origin", "days"}


def test_budget_without_scope_is_missing_info():
    request, missing, errors = validate_trip_request(
        origin="POS", days=5, budget_amount=500
    )

    assert request is None
    assert errors == []
    assert missing == [{
        "field": "budget_scope",
        "question": "Is that budget per person, or for the whole group?",
    }]


def test_budget_with_scope_and_defaults_succeeds():
    request, missing, errors = validate_trip_request(
        origin="POS",
        days=5,
        budget_amount=500,
        budget_scope="per_person",
    )

    assert missing == []
    assert errors == []
    assert request.travelers == 1
    assert request.budget_currency == "USD"


def test_invalid_travelers_is_an_error_not_missing_info():
    request, missing, errors = validate_trip_request(
        origin="POS", days=5, travelers=-1
    )

    assert request is None
    assert missing == []
    assert "travelers must be a positive whole number." in errors


def test_travel_date_in_the_past_is_rejected():
    request, missing, errors = validate_trip_request(
        origin="POS", days=5, travel_date="2000-01-01"
    )

    assert request is None
    assert "travel_date cannot be in the past." in errors


def test_return_date_before_travel_date_is_rejected():
    request, missing, errors = validate_trip_request(
        origin="POS",
        days=5,
        travel_date="2030-06-10",
        return_date="2030-06-01",
    )

    assert request is None
    assert "return_date cannot be before travel_date." in errors


def test_valid_request_round_trips_cleanly():
    request, missing, errors = validate_trip_request(
        origin="  Barbados  ",
        days=7,
        travelers=3,
        preferences={"beach": 1.0},
        budget_amount=1200,
        budget_currency="usd",
        budget_scope="group",
    )

    assert missing == []
    assert errors == []
    assert request.origin == "Barbados"
    assert request.travelers == 3
    assert request.budget_currency == "USD"
    assert request.preferences == {"beach": 1.0}
