"""
scripted_demo.py

A reproducible end-to-end walkthrough of WeyWeGoing? that needs no API
keys and no network access, by mocking only the Groq chat completion
call itself. Everything else - request validation, tool selection
handling, deterministic ranking, route lookup, flight quote lookup
(demo mode), and budget math - is the real code path.

Run it from the repo root:

    python3 examples/scripted_demo.py

Turn 1 shows the agent asking a follow-up question when the origin is
missing, instead of guessing it. Turn 2 shows a full recommendation with
a demo flight quote and a flights-only budget check attached.

To see this same flow with a REAL LLM choosing the tool calls, set
GROQ_API_KEY in .env and run `python3 main.py` instead - the tool-calling
and rendering code exercised here is identical either way.
"""

import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent as agent_module
import config
import main
from agent import run_agent

config.LLM_CONFIGURED = True
config.GROQ_API_KEY = "fake-for-demo"


def _tool_call(call_id, name, arguments):
    call = MagicMock()
    call.id = call_id
    call.function.name = name
    call.function.arguments = json.dumps(arguments)
    return call


def _scripted_response(tool_calls=None, content=None):
    message = MagicMock()
    message.tool_calls = tool_calls
    message.content = content
    return MagicMock(choices=[MagicMock(message=message)])


def run_turn(user_message, scripted_responses, conversation_history=None):
    agent_module._client = None  # force a fresh mocked client each turn

    with patch("agent.Groq") as mock_groq_class:
        mock_groq_class.return_value.chat.completions.create.side_effect = (
            scripted_responses
        )
        outcome = run_agent(user_message, conversation_history)

    main.render_tool_trace(outcome["tool_calls"])
    print(f"\nAgent reply: {outcome['reply']}\n")

    return outcome


def main_demo():
    print("=" * 70)
    print("TURN 1: \"Plan a 5 day beach trip\" (no origin given)")
    print("=" * 70)

    turn1 = run_turn(
        "Plan a 5 day beach trip",
        [
            _scripted_response(
                tool_calls=[_tool_call("1", "recommend_destinations", {
                    "days": 5,
                })]
            ),
            _scripted_response(
                content=(
                    "Where are you departing from? I need that to search "
                    "flights and routes."
                )
            ),
        ],
    )

    print("=" * 70)
    print("TURN 2: user supplies origin, date, travelers, budget")
    print("=" * 70)

    run_turn(
        "I'm leaving from Trinidad on 2026-12-10, 2 of us, $900 each, "
        "per person, we love the beach",
        [
            _scripted_response(
                tool_calls=[_tool_call("2", "recommend_destinations", {
                    "days": 5,
                    "origin": "Trinidad",
                    "travel_date": "2026-12-10",
                    "travelers": 2,
                    "budget_amount": 900,
                    "budget_currency": "USD",
                    "budget_scope": "per_person",
                    "preferences": {"beach": 1.0, "relaxation": 0.8},
                })]
            ),
            _scripted_response(
                content=(
                    "Here are your top Caribbean matches. Flight prices "
                    "are DEMO estimates (no Amadeus credentials "
                    "configured), not real fares, and the budget check "
                    "only covers flights - not the whole trip."
                )
            ),
        ],
        conversation_history=turn1["messages"],
    )


if __name__ == "__main__":
    main_demo()
