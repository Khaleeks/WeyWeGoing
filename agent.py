"""
agent.py

The WeyWeGoing? agent loop.

The LLM receives a set of tools from tools.py and decides which tool
to call based on what the user is asking. Tool results are then sent
back to the model so it can produce a grounded final reply.
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
        "GROQ_API_KEY was not found. Add it to your .env file."
    )

_client = Groq(api_key=_api_key)

MODEL = "openai/gpt-oss-120b"

SYSTEM_PROMPT = """You are the WeyWeGoing? travel agent, helping people plan
Caribbean trips.

You have tools that return SEEDED DEMO DATA about destinations, routes,
weather, costs, and currencies. The data is for prototyping and is not
live travel information.

Never invent a price, route, weather condition, exchange rate, score,
or destination fact. If the user asks for one of those, call the
appropriate tool.

Use:
- recommend_destinations for a new trip request with a budget and trip length. If the user gives a travel month, pass it to the tool so weather can affect ranking. Use Trinidad/POS as the default origin unless the user gives another origin.
- get_destination_details for questions about one specific destination.
- check_route when the user asks whether or how two places are connected.
- get_weather when the user asks about weather or a month's typical conditions.
- convert_currency when the user asks to convert money between currencies.

If a tool needs information the user did not provide, ask for it instead
of guessing.

After getting a tool result, explain it naturally and clearly. Keep the
answer grounded in the returned tool data. Do not add specific facts that
were not returned by a tool.
"""

MAX_TOOL_ITERATIONS = 5


def _execute_tool_call(tool_call):
    """Runs the Python function requested by the model."""
    name = tool_call.function.name

    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return {
            "status": "error",
            "message": "Could not parse tool arguments."
        }

    function = TOOL_FUNCTIONS.get(name)

    if function is None:
        return {
            "status": "error",
            "message": f"Unknown tool: {name}"
        }

    return function(**arguments)


def run_agent(user_message, conversation_history=None):
    """
    Runs one full turn of the agent.

    The model may call several tools before producing its final answer.
    """
    messages = list(conversation_history or [])

    if not messages or messages[0].get("role") != "system":
        messages.insert(
            0,
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        )

    messages.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    tool_call_trace = []

    for _ in range(MAX_TOOL_ITERATIONS):
        response = _client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_choice="auto",
            temperature=0.2,
        )

        message = response.choices[0].message

        if not message.tool_calls:
            messages.append({
                "role": "assistant",
                "content": message.content
            })

            return {
                "reply": message.content,
                "tool_calls": tool_call_trace,
                "messages": messages,
            }

        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tool_call.id,
                    "type": "function",
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            result = _execute_tool_call(tool_call)

            try:
                arguments = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                arguments = {}

            tool_call_trace.append({
                "name": tool_call.function.name,
                "arguments": arguments,
                "result": result,
            })

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    return {
        "reply": (
            "I wasn't able to finish processing that request. "
            "Try rephrasing it."
        ),
        "tool_calls": tool_call_trace,
        "messages": messages,
    }
