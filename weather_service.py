"""
weather_service.py

All WeatherAPI.com logic lives here.

This keeps API code out of planner.py and tools.py, so both parts of the
project can use the same weather function.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")

BASE_URL = "https://api.weatherapi.com/v1"


def get_forecast(airport_code, days=3):
    """
    Gets a real weather forecast from WeatherAPI.com.

    The free WeatherAPI plan supports up to 3 forecast days, so this
    project intentionally caps requests at 3 days.
    """
    if not WEATHER_API_KEY:
        raise ValueError(
            "WEATHER_API_KEY is missing. "
            "Add it to your .env file."
        )

    days = max(1, min(int(days), 3))

    url = f"{BASE_URL}/forecast.json"

    params = {
        "key": WEATHER_API_KEY,
        "q": f"iata:{airport_code}",
        "days": days,
        "aqi": "no",
        "alerts": "no",
    }

    response = requests.get(
        url,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    data = response.json()

    forecast = []

    for forecast_day in data["forecast"]["forecastday"]:
        day = forecast_day["day"]

        forecast.append({
            "date": forecast_day["date"],
            "average_temp_c": day["avgtemp_c"],
            "max_temp_c": day["maxtemp_c"],
            "min_temp_c": day["mintemp_c"],
            "rain_probability": day["daily_chance_of_rain"],
            "condition": day["condition"]["text"],
        })

    return {
        "location": {
            "name": data["location"]["name"],
            "region": data["location"]["region"],
            "country": data["location"]["country"],
        },
        "forecast": forecast,
    }


def get_weather_for_date(airport_code, travel_date):
    """
    Returns weather for one exact date if that date is inside the
    available 3-day forecast.

    If the date is outside the forecast window, returns None.
    """
    weather_data = get_forecast(
        airport_code,
        days=3
    )

    for day in weather_data["forecast"]:
        if day["date"] == travel_date:
            return day

    return None
