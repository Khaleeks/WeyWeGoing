# WeyWeGoing? 🌴✈️

An AI travel intelligence agent for Caribbean trip planning. Instead of
searching flights and hotels separately, you describe your trip in plain
language — budget, time, what you want to do — and WeyWeGoing? works out
which destinations are actually realistic, with an itemized cost
breakdown and an explainable match score.

> "I have TT$3500 and a long weekend. Somewhere with beach and nightlife."

## Why this isn't just a ChatGPT wrapper

The LLM doesn't just parse your sentence and hand off to a fixed
pipeline — it's given a set of tools (`tools.py`) and decides for
itself which to call and when: `recommend_destinations` for a new trip
request, `get_destination_details` for a follow-up about one specific
place. It can call a tool, look at the result, and call another before
replying. The system prompt also tells it never to state a cost, score,
or destination fact from its own "knowledge" — only from a tool result
— so the numbers you see always trace back to `planner.py`/`scoring.py`,
not the model's guess. Cost calculation and the WeyWeGoing Score
themselves remain plain, deterministic Python with no LLM involvement.

## Runs on Groq

`agent.py` calls Groq's LLM API (`openai/gpt-oss-120b`) with function
calling enabled. A `GROQ_API_KEY` is required — there's no offline
fallback, since the point of this project is to demonstrate real
LLM/agent integration rather than route around it.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env   # add your GROQ_API_KEY
python main.py
```

## Current architecture

```text
main.py        — CLI loop: sends input to the agent, renders tool results
agent.py       — the agent loop (Groq LLM decides which tools to call)
tools.py       — tool schemas + the functions they call (recommend, lookup)
planner.py     — loads destinations, computes itemized trip cost, ranks
scoring.py     — the WeyWeGoing Score (plain arithmetic, no LLM)
data/
  destinations.json       — seeded destination data (see caveat below)
```

## A note on the data

`destinations.json` currently holds **seeded estimates**, not sourced
flight/hotel prices or real review data. That's fine for building the
scoring and planning logic against something realistic-shaped, but it's
not yet ground-truth. The next milestone is swapping in a real flights
API (Amadeus / Kiwi Tequila) for at least the flight-price and
route-existence fields, so the "hallucinated route" question actually
means something.

## Roadmap

- [x] Tool-calling agent loop — LLM decides which tool(s) to call
      rather than running a fixed pipeline
- [ ] `routes.json` + a `check_route` tool — model Trinidad's actual
      Caribbean connections as a graph, so the agent can check whether
      a destination is really reachable instead of assuming it is
- [ ] `weather.json` (or a live API) + a `get_weather` tool — feeds
      into the score once it exists
- [ ] Eval suite (`evals/`): a test set of example queries checking
      tool-choice accuracy (did it call the right tool?), budget
      compliance, and whether replies stay grounded in tool results
      rather than the LLM's guess
- [ ] Swap seeded destination costs for a real flights/hotels API —
      once the tool set is stable, this becomes a change to
      `planner.py`/`tools.py` only, not the agent loop
- [ ] FastAPI backend + simple web frontend
- [ ] Route Radar (tracks new/changing Caribbean flight routes) — later,
      after the core loop is solid

## Example session

```text
> I have $3500 TTD and a long weekend. Somewhere with beach and nightlife.

[tool call: recommend_destinations({'budget': 3500, 'days': 3, 'preferences': {'beach': 1.0, 'nightlife': 1.0}})]

🥇 Grenada (GND)
WeyWeGoing Score: 77.0 / 100
  (budget fit: 80.0 | preference match: 75.0)

  ✈ Flight        TT$1100
  🏨 Accommodation TT$900
  🍛 Food          TT$750
  🚕 Transport     TT$300
  🎉 Activities    TT$450
  ─────────────────────────
  Estimated Total  TT$3500
  Remaining buffer TT$0

Grenada is your best fit — strong beach and nightlife scores, and it
uses your full budget with no buffer left over.

> tell me more about barbados

[tool call: get_destination_details({'name': 'barbados'})]

📍 Barbados (BGI)
  Estimated flight: TT$1400
  Ideal trip length: 4 days
  Scores (0-10):
    beach: 9
    nightlife: 9
    ...

Barbados scores just as high on beach and nightlife as Grenada, but
runs a pricier flight and daily costs.
```