"""
agent.py

Turns a natural-language travel request into structured preferences
using Groq's LLM API. No fallback path -- if GROQ_API_KEY is missing
or the API call fails, this raises rather than silently degrading,
since the point of this project is to demonstrate real agent/LLM
integration, not paper over it.
"""

import json
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")

if not _api_key:
    raise ValueError(
        "GROQ_API_KEY was not found. Add it to your .env file."
    )

_client = Groq(api_key=_api_key)

MODEL = "openai/gpt-oss-120b"

PREFERENCE_CATEGORIES = [
    "beach", "nightlife", "food", "culture",
    "nature", "romantic", "adventure", "relaxation",
]


def extract_preferences(user_message):
    """
    Returns:
    {
        "budget": int | None,
        "days": int | None,
        "preferences": { "<category>": 0.0-1.0, ... }
    }
    """
    categories_list = ", ".join(PREFERENCE_CATEGORIES)

    system_prompt = f"""You are parsing a Caribbean travel request for an app called WeyWeGoing?.

Extract:
- budget: integer in TTD, or null if missing
- days: integer, or null if missing
- preferences: an object mapping any of these categories to a weight
  from 0.0 to 1.0 based on how strongly the user expressed interest:
  {categories_list}
  Only include categories the user actually implied. Omit the rest.

Interpret common phrases naturally:
- "weekend" = 2 days, "long weekend" = 3 days
- "3k" = 3000, "4k" = 4000

Respond with ONLY valid JSON in this exact structure, nothing else:
{{
  "budget": null,
  "days": null,
  "preferences": {{}}
}}"""

    response = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )

    content = response.choices[0].message.content
    return json.loads(content)
