from scoring import (
    calculate_weywegoing_score,
    score_preference_match,
    score_route_convenience,
    score_weather_fit,
)


def test_preference_match_no_preferences_is_neutral():
    assert score_preference_match({"beach": 10}, {}) == 60


def test_preference_match_weights_by_stated_interest():
    destination_scores = {"beach": 10, "nightlife": 0}

    # Only beach stated as important -> should approach 100.
    result = score_preference_match(
        destination_scores, {"beach": 1.0}
    )
    assert result == 100

    # Only nightlife stated -> destination scores 0 there.
    result = score_preference_match(
        destination_scores, {"nightlife": 1.0}
    )
    assert result == 0


def test_preference_match_ignores_non_positive_weights():
    destination_scores = {"beach": 10, "nightlife": 2}

    result = score_preference_match(
        destination_scores, {"beach": 1.0, "nightlife": 0}
    )

    assert result == 100


def test_preference_match_missing_category_defaults_mid_score():
    # Destination has no "culture" entry -> treated as a neutral 5/10.
    result = score_preference_match({}, {"culture": 1.0})
    assert result == 50


def test_route_convenience_scores():
    assert score_route_convenience("direct") == 100
    assert score_route_convenience("one_stop") == 70
    assert score_route_convenience("unknown") == 50


def test_weather_fit_neutral_without_data():
    assert score_weather_fit(None) == 60
    assert score_weather_fit({"rain_probability": None}) == 60


def test_weather_fit_scales_with_rain_probability():
    assert score_weather_fit({"rain_probability": 10}) == 100
    assert score_weather_fit({"rain_probability": 35}) == 85
    assert score_weather_fit({"rain_probability": 55}) == 65
    assert score_weather_fit({"rain_probability": 75}) == 45
    assert score_weather_fit({"rain_probability": 95}) == 25


def test_final_score_is_weighted_combination():
    result = calculate_weywegoing_score(
        destination_scores={"beach": 10},
        user_preferences={"beach": 1.0},
        route_type="direct",
        weather={"rain_probability": 10},
    )

    # preference=100*0.6 + route=100*0.25 + weather=100*0.15 = 100
    assert result["final_score"] == 100.0
    assert result["preference_match"] == 100.0
    assert result["route_convenience"] == 100
    assert result["weather_fit"] == 100


def test_final_score_matches_manual_weighted_sum():
    result = calculate_weywegoing_score(
        destination_scores={"beach": 4},
        user_preferences={"beach": 1.0},
        route_type="one_stop",
        weather=None,
    )

    # preference = 40, route = 70, weather = 60 (neutral)
    expected = round(40 * 0.60 + 70 * 0.25 + 60 * 0.15, 1)
    assert result["final_score"] == expected
