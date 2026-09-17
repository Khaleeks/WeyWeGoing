"""
agent.py

Runs the WeyWeGoing? tool-calling agent using Groq.
"""

import json

from groq import Groq

import config
from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

MODEL = "openai/gpt-oss-120b"

_client = None


def _get_client():
    """Creates the Groq client lazily so a missing key doesn't crash on
    import - it only fails when the agent is actually asked to run."""
    global _client

    config.require(
        config.LLM_CONFIGURED,
        config.GROQ_SETUP_MESSAGE,
    )

    if _client is None:
        _client = Groq(api_key=config.GROQ_API_KEY)

    return _client

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """
You are the WeyWeGoing? Caribbean travel agent.

WeyWeGoing? is intentionally limited to Caribbean destinations.

Current data:
- destinations.json contains the supported Caribbean destination catalog,
  airport codes, currencies, region types, and temporary preference scores.
- Weather comes from the real WeatherAPI.com API.
- Route data (check_route) is still seeded and incomplete - it only
  covers a handful of legs.
- Currency exchange rates come from the live Frankfurter API.
- Flight prices come from get_flight_quote / recommend_destinations. They
  are EITHER a real sandbox quote from Amadeus's TEST environment (sample
  inventory, not production live pricing) OR, if no flight credentials
  are configured, a clearly-labeled demo estimate. The tool result's
  "data_type" field tells you which - always say which kind of price you
  are showing, never call a demo estimate a real fare, and never call a
  sandbox quote "live" (it's the test environment, not production).
- Hotel, food, transport, and activity pricing is NOT connected. If asked
  about them, say so plainly.

Tools:
- recommend_destinations: ranks destinations by preference/route/weather
  fit, and (when travel_date is given) attaches a flight quote and a
  flights-only budget check to each result.
- get_flight_quote: a standalone flight price for one specific
  origin/destination/date, when the user just wants a price.
- get_destination_details: metadata for one supported destination.
- check_route: whether the seeded route dataset covers a leg.
- get_weather: near-term forecast for a Caribbean location.
- convert_currency: live currency conversion.

Understanding the request:
- Never invent essential trip details. If recommend_destinations returns
  status "missing_info", ask the user exactly the listed follow-up
  question(s) instead of guessing - including where they're departing
  from (there is no default origin), the trip length or dates, and,
  whenever they mention a budget, whether it's per person or for the
  whole group.
- If the tool returns status "invalid_request", explain the problem in
  plain language and ask the user to correct it.
- Only include preferences the user actually expressed.
- Only pass travel_date/return_date when the user gave an exact date -
  never invent one from a vague month like "sometime in February".
- Ask for the number of travelers if a budget is mentioned and the count
  isn't clear; otherwise 1 traveler is assumed and you should say so.
- Unknown route data does not mean a route does not exist; it means the
  current seeded route dataset does not cover it yet.
- Weather affects ranking only when usable real forecast data is
  available for the exact date.

Presenting costs (do this every time a flight quote is shown):
- State whether the price is a live-labeled sandbox quote or a demo
  estimate, its currency, and when it was retrieved.
- If a budget was given, only say whether the FLIGHT portion fits - never
  claim the whole trip fits a budget from airfare alone. Mention that
  accommodation, food, local transport, and activities are excluded.
- Remind the user that prices and availability can change and this
  quote was refreshed just now, not cached from earlier.

After tool results, explain them clearly without claiming data the system
doesn't actually have.
"""


def _execute_tool_call(tool_call):
    """Runs one tool requested by the model."""
    function_name = tool_call.function.name

    try:
        arguments = json.loads(
            tool_call.function.arguments
        )

    except json.JSONDecodeError:
        arguments = {}

    if function_name not in TOOL_FUNCTIONS:
        return {
            "status": "error",
            "message": (
                f"Unknown tool: "
                f"{function_name}"
            ),
        }, arguments

    try:
        result = TOOL_FUNCTIONS[
            function_name
        ](**arguments)

    except Exception as error:
        result = {
            "status": "error",
            "message": str(error),
        }

    return result, arguments


def run_agent(
    user_message,
    conversation_history=None
):
    """Runs the tool-calling conversation loop."""
    try:
        client = _get_client()
    except config.MissingCredentialsError as error:
        return {
            "reply": str(error),
            "tool_calls": [],
            "messages": conversation_history or [],
            "error": "missing_credentials",
        }

    if conversation_history:
        messages = list(
            conversation_history
        )

        messages.append({
            "role": "user",
            "content": user_message,
        })

    else:
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_message,
            },
        ]

    tool_trace = []

    for _ in range(
        MAX_TOOL_ITERATIONS
    ):
        response = (
            client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOL_SCHEMAS,
                tool_choice="auto",
            )
        )

        message = (
            response.choices[0].message
        )

        messages.append(message)

        if not message.tool_calls:
            return {
                "reply": (
                    message.content or ""
                ),
                "tool_calls": tool_trace,
                "messages": messages,
            }

        for tool_call in message.tool_calls:
            result, arguments = (
                _execute_tool_call(
                    tool_call
                )
            )

            tool_trace.append({
                "name": (
                    tool_call.function.name
                ),
                "arguments": arguments,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(
                    result
                ),
            })

    return {
        "reply": (
            "I reached the maximum number "
            "of tool calls for this request."
        ),
        "tool_calls": tool_trace,
        "messages": messages,
    }
