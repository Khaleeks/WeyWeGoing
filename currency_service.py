"""
currency_service.py

Handles live currency conversion using the Frankfurter API.
"""

import requests

BASE_URL = "https://api.frankfurter.dev/v2"


def get_exchange_rate(
    from_currency,
    to_currency
):
    """
    Gets the latest exchange rate between two currencies.
    """

    from_code = from_currency.upper()
    to_code = to_currency.upper()

    if from_code == to_code:
        return {
            "from_currency": from_code,
            "to_currency": to_code,
            "rate": 1.0,
            "date": None,
        }

    url = (
        f"{BASE_URL}/rate/"
        f"{from_code}/{to_code}"
    )

    response = requests.get(
        url,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    return {
        "from_currency": from_code,
        "to_currency": to_code,
        "rate": data["rate"],
        "date": data["date"],
    }


def convert_currency(
    amount,
    from_currency,
    to_currency
):
    """
    Converts an amount using the latest Frankfurter rate.
    """

    exchange_data = get_exchange_rate(
        from_currency,
        to_currency
    )

    converted_amount = (
        amount * exchange_data["rate"]
    )

    return {
        "amount": amount,
        "from_currency": (
            exchange_data["from_currency"]
        ),
        "to_currency": (
            exchange_data["to_currency"]
        ),
        "rate": exchange_data["rate"],
        "converted_amount": round(
            converted_amount,
            2
        ),
        "date": exchange_data["date"],
    }