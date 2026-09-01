"""
agent.py

Runs the WeyWeGoing? tool-calling agent using Groq.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq

from tools import TOOL_FUNCTIONS, TOOL_SCHEMAS

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")

if not _api_key:
    raise ValueError(
        "GROQ_API_KEY is missing. "
        "Add it to your .env file."
    )

_client = Groq(
    api_key=_api_key
)

MODEL = "openai/gpt-oss-120b"

MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """
You are the WeyWeGoing? Caribbean travel agent.

WeyWeGoing? is intentionally limited to Caribbean destinations.

Current data:
- destinations.json contains the supported Caribbean destination catalog,
  airport codes, currencies, region types, and temporary preference scores.
- Weather comes from the real WeatherAPI.com API.
- Route data is still seeded and incomplete.
- Currency exchange rates come from the live Frankfurter API.
- Real flight, hotel, food, transport, and activity pricing is NOT
  connected yet.

Use:
- recommend_destinations for destination recommendations.
- get_destination_details for one supported Caribbean destination.
- check_route for route questions.
- get_weather for current or near-term Caribbean weather.
- convert_currency for live currency conversions using Frankfurter.

Recommendation rules:
- Use Trinidad/POS as the default origin unless the user gives another.
- Only include preferences the user actually expressed.
- If the user provides a budget, pass it to the recommendation tool, but
  do not claim the system has checked affordability. Real pricing is not
  connected yet.
- If the user gives an exact travel date, pass travel_date as YYYY-MM-DD.
- Do not invent an exact date from a month such as "February".
- Unknown route data does not mean a route does not exist; it means the
  current seeded route dataset does not cover it yet.
- Weather affects ranking only when usable real forecast data is available.

If the user asks for exact trip prices, flight prices, hotel prices, or a
budget-fit claim, explain that live pricing has not been connected yet.

After tool results, explain the result clearly without claiming unsupported
live data.
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
            _client.chat.completions.create(
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
