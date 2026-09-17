from unittest.mock import Mock, patch

import pytest
import requests

from currency_service import convert_currency, get_exchange_rate


def _mock_response(json_data, status_code=200):
    response = Mock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status = Mock()

    if status_code >= 400:
        response.raise_for_status.side_effect = requests.HTTPError(
            f"{status_code} error"
        )

    return response


def test_same_currency_shortcut_makes_no_request():
    with patch("currency_service.requests.get") as mock_get:
        result = get_exchange_rate("USD", "usd")

        mock_get.assert_not_called()
        assert result["rate"] == 1.0
        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "USD"


def test_convert_currency_uses_live_rate_and_rounds():
    fake_response = _mock_response({"rate": 3.5, "date": "2026-01-01"})

    with patch(
        "currency_service.requests.get", return_value=fake_response
    ) as mock_get:
        result = convert_currency(100, "USD", "TTD")

        mock_get.assert_called_once()
        assert result["converted_amount"] == 350.0
        assert result["rate"] == 3.5
        assert result["date"] == "2026-01-01"
        assert result["from_currency"] == "USD"
        assert result["to_currency"] == "TTD"


def test_convert_currency_propagates_http_errors():
    fake_response = _mock_response({}, status_code=404)

    with patch(
        "currency_service.requests.get", return_value=fake_response
    ):
        with pytest.raises(requests.HTTPError):
            convert_currency(100, "USD", "ZZZ")


def test_convert_currency_propagates_timeouts():
    with patch(
        "currency_service.requests.get",
        side_effect=requests.exceptions.Timeout,
    ):
        with pytest.raises(requests.exceptions.Timeout):
            convert_currency(100, "USD", "EUR")
