"""
config.py

Central place that knows which external providers are configured.

Nothing in this file makes network calls. Its only job is to tell the
rest of the app "live mode" vs "demo mode" for each provider, and to
produce a helpful setup message instead of letting a missing API key
crash the process.
"""

import os

from dotenv import load_dotenv

load_dotenv()


def _clean(value):
    return value.strip() if value else None


GROQ_API_KEY = _clean(os.getenv("GROQ_API_KEY"))
WEATHER_API_KEY = _clean(os.getenv("WEATHER_API_KEY"))
AMADEUS_CLIENT_ID = _clean(os.getenv("AMADEUS_CLIENT_ID"))
AMADEUS_CLIENT_SECRET = _clean(os.getenv("AMADEUS_CLIENT_SECRET"))

LLM_CONFIGURED = bool(GROQ_API_KEY)
WEATHER_CONFIGURED = bool(WEATHER_API_KEY)
FLIGHTS_CONFIGURED = bool(AMADEUS_CLIENT_ID and AMADEUS_CLIENT_SECRET)

# Frankfurter (currency) needs no API key, so it has no "configured" flag.


class MissingCredentialsError(Exception):
    """Raised when a live provider is called without its API key(s)."""


def require(flag, message):
    if not flag:
        raise MissingCredentialsError(message)


GROQ_SETUP_MESSAGE = (
    "GROQ_API_KEY is missing, so the natural-language agent can't run.\n"
    "1. Create a free key at https://console.groq.com/keys\n"
    "2. Add it to your .env file as GROQ_API_KEY=...\n"
    "3. Restart the app.\n"
    "(Everything else - weather, currency, flights, scoring - works "
    "independently of this key.)"
)

WEATHER_SETUP_MESSAGE = (
    "WEATHER_API_KEY is missing, so live weather isn't available.\n"
    "Get a free key at https://www.weatherapi.com/signup.aspx and add it "
    "to .env as WEATHER_API_KEY=...\n"
    "Recommendations still work without it - weather just falls back to "
    "a neutral score."
)

FLIGHTS_SETUP_MESSAGE = (
    "AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET are missing, so flight "
    "prices are running in DEMO mode (clearly-labeled estimates, not "
    "real fares).\n"
    "For real sandbox flight quotes:\n"
    "1. Create a free account at https://developers.amadeus.com\n"
    "2. Create a 'Self-Service' app to get a test-environment API key "
    "and secret (no cost, no credit card).\n"
    "3. Add them to .env as AMADEUS_CLIENT_ID=... and "
    "AMADEUS_CLIENT_SECRET=...\n"
    "Note: even with real credentials, Amadeus's free tier is a TEST "
    "environment with sample inventory, not production live pricing."
)


def status_summary():
    """A small dict the CLI/Streamlit UI can render as a mode banner."""
    return {
        "llm": {
            "configured": LLM_CONFIGURED,
            "mode": "live" if LLM_CONFIGURED else "unavailable",
            "message": None if LLM_CONFIGURED else GROQ_SETUP_MESSAGE,
        },
        "weather": {
            "configured": WEATHER_CONFIGURED,
            "mode": "live" if WEATHER_CONFIGURED else "unavailable",
            "message": None if WEATHER_CONFIGURED else WEATHER_SETUP_MESSAGE,
        },
        "flights": {
            "configured": FLIGHTS_CONFIGURED,
            "mode": "sandbox" if FLIGHTS_CONFIGURED else "demo",
            "message": None if FLIGHTS_CONFIGURED else FLIGHTS_SETUP_MESSAGE,
        },
        "currency": {
            "configured": True,
            "mode": "live",
            "message": None,
        },
    }
