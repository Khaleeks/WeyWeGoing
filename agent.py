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
You are the WeyWeGoing? travel agent.

WeyWeGoing? helps users make realistic Caribbean travel decisions based
on budget, time, interests, routes, weather, and currency.

Use the available tools whenever the user asks for information that the
tools can provide.

Important data rules:
- Destination profiles and cost estimates are still seeded demo data.
- Route data is still seeded demo data.
- Currency exchange rates are still seeded demo data.
- Weather now comes from the real WeatherAPI.com forecast API.

Use:
- recommend_destinations for a new trip request with a budget and trip
  length.
- get_destination_details for questions about one specific destination.
- check_route when the user asks whether or how two places are connected.
- get_weather for current or near-term forecast questions.
- convert_currency when the user asks to convert money.

For recommend_destinations:
- Use Trinidad/POS as the default origin unless the user gives another
  origin.
- Only include preferences the user actually expressed.
- If the user provides an exact travel date, pass it as travel_date in
  YYYY-MM-DD format.
- Do not invent an exact date from only a month such as "February".
- If no exact travel date is given, omit travel_date. The recommendation
  engine will use a neutral weather score.

WeatherAPI's free forecast window is short. Do not claim that the weather
tool can provide a reliable forecast for a date outside the returned
forecast data.

If a tool needs required information the user did not provide, ask for
it instead of guessing.

After receiving tool results, explain them naturally and clearly.
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
    """
    Sends the user's message to the LLM and allows it to call tools.
    """
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
