"""
tools.py

Defines the tools the agent can choose to call, in the JSON schema
format Groq's (OpenAI-compatible) function-calling API expects, plus
the actual Python functions that run when a tool is called.

Two tools for now, on purpose:
- recommend_destinations: for a new trip request (budget/time/vibe)
- get_destination_details: for a follow-up about one specific place

Both are thin wrappers around planner.py -- no new data source, same
seeded destinations.json as before. This file only changes *how* the
LLM reaches that logic (by choosing to call it), not *what* data
backs it.
"""

from planner import load_destinations, recommend_destinations as _recommend_destinations


def recommend_destinations_tool(budget, days, preferences=None):
    """
    Wraps planner.recommend_destinations. Called when the user
    describes a new trip: a budget, a length of stay, and optionally
    what they want out of it.
    """
    results = _recommend_destinations(
        budget=budget,
        days=days,
        preferences=preferences or {},
    )

    if not results:
        return {"status": "no_matches", "results": []}

    return {"status": "ok", "results": results}


def get_destination_details_tool(name):
    """
    Wraps a lookup into destinations.json. Called when the user asks
    about one specific place rather than requesting a new
    recommendation -- e.g. "tell me more about Grenada".
    """
    destinations = load_destinations()

    for destination in destinations:
        if destination["name"].lower() == name.lower():
            return {"status": "ok", "destination": destination}

    available = [d["name"] for d in destinations]
    return {
        "status": "not_found",
        "message": f"No destination named '{name}' in the current dataset.",
        "available_destinations": available,
    }


# Maps tool name (as the LLM will refer to it) -> the function to run.
TOOL_FUNCTIONS = {
    "recommend_destinations": recommend_destinations_tool,
    "get_destination_details": get_destination_details_tool,
}

# JSON schemas describing each tool to the LLM. This is what the LLM
# actually reads to decide whether and how to call a tool -- the
# description fields matter a lot for getting good tool-choice
# behavior, not just the parameter types.
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "recommend_destinations",
            "description": (
                "Recommend Caribbean destinations for a NEW trip request. "
                "Use this when the user describes a budget, a trip length, "
                "and/or what they want out of the trip (beach, nightlife, "
                "food, culture, nature, romance, adventure, relaxation). "
                "Do not guess costs or destinations yourself -- always call "
                "this tool to get real numbers from the dataset."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "budget": {
                        "type": "integer",
                        "description": "Total trip budget in TTD.",
                    },
                    "days": {
                        "type": "integer",
                        "description": "Length of the trip in days.",
                    },
                    "preferences": {
                        "type": "object",
                        "description": (
                            "Weighted interests, each 0.0-1.0. Only include "
                            "categories the user actually implied. Valid "
                            "keys: beach, nightlife, food, culture, nature, "
                            "romantic, adventure, relaxation."
                        ),
                        "properties": {
                            "beach": {"type": "number"},
                            "nightlife": {"type": "number"},
                            "food": {"type": "number"},
                            "culture": {"type": "number"},
                            "nature": {"type": "number"},
                            "romantic": {"type": "number"},
                            "adventure": {"type": "number"},
                            "relaxation": {"type": "number"},
                        },
                    },
                },
                "required": ["budget", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_destination_details",
            "description": (
                "Look up full details for ONE specific destination the "
                "user asks about directly -- e.g. 'tell me more about "
                "Grenada' or 'what's the food like in Barbados'. Do not "
                "use this for a new trip request; use recommend_destinations "
                "instead. Do not describe a destination from your own "
                "knowledge -- always call this tool for real data."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Destination name, e.g. 'Grenada'.",
                    },
                },
                "required": ["name"],
            },
        },
    },
]