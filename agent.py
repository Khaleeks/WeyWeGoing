"""
agent.py

The agent loop. Unlike the old version of this file, the LLM here
doesn't just extract preferences and hand off to a fixed pipeline --
it's given a set of tools (see tools.py) and decides for itself
whether and how to call them, based on the conversation so far.

Flow per turn:
1. Send the conversation + tool schemas to Groq.
2. If the model responds with tool call(s), run the real Python
   functions, feed the results back as tool messages, and go again.
3. Once the model responds with plain text (no more tool calls),
   that's the final reply for this turn.

No fallback path -- if GROQ_API_KEY is missing or a call fails, this
raises rather than silently degrading.
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

You have tools that return REAL data (costs, scores, destination info).
You do not know real trip costs or destination details yourself -- never
state a price, score, or fact about a destination unless it came from a
tool result. If you don't have a tool result for something, say so and
call the right tool instead of guessing.

Use recommend_destinations for a new trip request (budget, trip length,
and/or preferences). Use get_destination_details when the user asks about
one specific place. If the user's message doesn't give you enough to call
a tool usefully (e.g. no budget or trip length at all), ask them for what's
missing instead of guessing.

After you get a tool result, explain it to the user in a short, natural
reply. Don't just repeat the raw numbers back verbatim -- summarize what
matters.
"""

MAX_TOOL_ITERATIONS = 5


def _execute_tool_call(tool_call):
    """Runs the real Python function for one tool call the model requested."""
    name = tool_call.function.name
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError:
        return {"status": "error", "message": "Could not parse tool arguments."}

    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return {"status": "error", "message": f"Unknown tool: {name}"}

    return function(**arguments)


def run_agent(user_message, conversation_history=None):
    """
    Runs one full turn of the agent loop (which may involve several
    tool calls before producing a final reply).

    conversation_history: optional list of prior {"role", "content"}
    messages, so callers can maintain a multi-turn conversation.

    Returns:
    {
        "reply": str,                 # final natural-language reply
        "tool_calls": [               # trace of every tool call made
            {"name": str, "arguments": dict, "result": dict},
            ...
        ],
        "messages": list,             # full updated message history
    }
    """
    messages = list(conversation_history or [])
    if not messages or messages[0].get("role") != "system":
        messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})

    messages.append({"role": "user", "content": user_message})

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
            messages.append({"role": "assistant", "content": message.content})
            return {
                "reply": message.content,
                "tool_calls": tool_call_trace,
                "messages": messages,
            }

        # Model wants to call one or more tools -- record its request,
        # run each tool for real, and feed results back.
        messages.append({
            "role": "assistant",
            "content": message.content,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in message.tool_calls
            ],
        })

        for tool_call in message.tool_calls:
            result = _execute_tool_call(tool_call)
            tool_call_trace.append({
                "name": tool_call.function.name,
                "arguments": json.loads(tool_call.function.arguments),
                "result": result,
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result),
            })

    # Hit MAX_TOOL_ITERATIONS without a final text reply -- surface
    # this clearly rather than silently returning nothing.
    return {
        "reply": "I wasn't able to finish processing that request in time -- try rephrasing it.",
        "tool_calls": tool_call_trace,
        "messages": messages,
    }