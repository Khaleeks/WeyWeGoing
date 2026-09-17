# WeyWeGoing? 🌴✈️

An AI-assisted Caribbean trip-planning agent. Describe a trip in plain
language - where you're leaving from, when, for how long, your budget,
who's travelling, what you like - and get ranked destination
recommendations with a transparent cost breakdown, clearly labeled by
data source.

This is a portfolio/interview project. It is intentionally scoped: one
region (the Caribbean), one paid-data category priced (flights), and
everything else either seeded, estimated, or explicitly marked as not
covered.

## What actually works right now

Verified by reading the code and running it (see "Demo walkthrough"
below for a working, reproducible run):

| Piece | Status |
|---|---|
| Natural-language request parsing (Groq LLM + tool calling) | Real |
| Departure/dates/travelers/budget validation, missing-info follow-ups | Real, deterministic |
| Destination ranking (preference + route + weather) | Real, deterministic |
| Weather | Real (WeatherAPI.com, 3-day forecast window) |
| Currency conversion | Real (Frankfurter, live rates) |
| Flight search | Real sandbox integration (Amadeus Self-Service **test** environment) with a labeled demo fallback when no credentials are configured |
| Budget check (flights only) | Real, deterministic |
| Route coverage (`data/routes.json`) | Seeded, ~10 legs, mostly from POS |
| Destination preference scores (`data/destinations.json`) | Seeded heuristic 0-10 ratings, not sourced from real survey/review data |
| Accommodation / food / activities pricing | **Not implemented** - explicitly excluded, never estimated |
| CLI (`main.py`) | Real, end to end |
| Streamlit UI (`streamlit_app.py`) | Real, end to end (chat tab + a direct-filter tab that bypasses the LLM) |
| Tests | 41 tests, mocked HTTP, no live network required |

## Architecture

```
User (natural language)
    |
    v
agent.py  --------------------------------  Groq LLM (tool-calling loop)
    | picks a tool + arguments                 |
    v                                          |
tools.py  (validates args, calls deterministic modules, never trusts
           the LLM's arithmetic)
    |
    +--> request_schema.py   Validates the extracted request. Missing
    |                        essentials (origin, dates, budget scope)
    |                        come back as follow-up questions, not
    |                        guesses.
    |
    +--> planner.py + scoring.py   Deterministic destination ranking:
    |                              preference match (60%) + route
    |                              convenience (25%) + weather fit (15%).
    |                              Pure Python, no LLM involved.
    |
    +--> weather_service.py         Live WeatherAPI.com forecast.
    +--> flight_service.py          Amadeus sandbox quote, or a labeled
    |                               demo estimate if unconfigured.
    +--> budget.py + currency_service.py
    |                               Deterministic flights-only budget
    |                               math, live FX conversion.
    v
Back to agent.py -> LLM explains the (already-computed) results in
                     natural language. It does not recompute scores,
                     prices, or budget fit - it only narrates them.
```

The LLM's job is narrow on purpose: interpret the user's sentence,
choose a tool, and explain the tool's result back in plain language.
Every number a user sees - the score, the flight price, the budget
comparison, the currency conversion - is produced by plain Python in
`scoring.py`, `budget.py`, `flight_service.py`, and `currency_service.py`,
and the LLM only ever receives already-computed JSON to describe.

### Request flow in one example

1. User: *"5 day beach trip, 2 of us, $900pp, leaving Trinidad Dec 10"*
2. `agent.py` sends this + tool schemas to Groq. The model calls
   `recommend_destinations` with `days=5, origin="Trinidad",
   travel_date="2026-12-10", travelers=2, budget_amount=900,
   budget_currency="USD", budget_scope="per_person",
   preferences={"beach": 1.0}`.
3. `tools.py` -> `request_schema.validate_trip_request(...)`. Everything
   essential is present, so it proceeds (if `origin` or `budget_scope`
   had been missing, it would return `status: "missing_info"` with the
   exact follow-up question, and the LLM is instructed to ask it rather
   than invent a default).
4. `planner.recommend_destinations` ranks all Caribbean destinations
   using `scoring.py` (preference/route/weather), independent of budget.
5. For the top-ranked destinations, `tools.py` calls
   `flight_service.search_flights(...)` (sandbox quote or demo estimate)
   and `budget.evaluate_flight_budget(...)` (deterministic, currency-
   converted via `currency_service.py`).
6. The combined JSON (ranking + route + weather + flight quote + budget
   check) goes back to the LLM, which narrates it - `main.py` and
   `streamlit_app.py` also render it directly and identically, so what
   you see doesn't depend on the LLM's phrasing.

## Live mode vs demo mode

Every provider reports its own mode; nothing crashes on a missing key.

| Provider | Live requires | Without it |
|---|---|---|
| Agent (Groq LLM) | `GROQ_API_KEY` | Chat can't run; CLI/Streamlit print setup instructions instead of a stack trace. The filter-based Streamlit tab still works fully without this key. |
| Weather | `WEATHER_API_KEY` | Weather score falls back to a neutral value; ranking still works. |
| Flights | `AMADEUS_CLIENT_ID` + `AMADEUS_CLIENT_SECRET` | A clearly-labeled **demo estimate** (deterministic placeholder, not a real fare) is shown instead. |
| Currency | none needed | Always live (Frankfurter has no auth). |

Every flight quote and every tool result carries a `data_type` field
(`"sandbox_quote"` or `"demo_estimate"`) and a human-readable `source`
string, so the UI, the CLI, and the LLM's explanation all say plainly
which kind of number is being shown. **A demo estimate is never labeled
as live, and an Amadeus test-environment quote is never called
"live"/"production" pricing** - Amadeus's own free tier is documented as
sample/cached inventory for development, not real-time fares.

Budget checks only ever compare against **flight cost**. Accommodation,
food, local transport, and activities are not priced anywhere in this
project, and every budget result says so explicitly rather than implying
the whole trip fits.

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# edit .env with whichever keys you have - all are optional
```

Run the CLI:

```bash
python3 main.py
```

Run the Streamlit UI:

```bash
streamlit run streamlit_app.py
```

Run the tests (no network or API keys needed - all HTTP is mocked):

```bash
pytest -q
```

## Demo walkthrough

The fastest way to see the whole pipeline (agent loop, validation,
ranking, flight quote, budget check, rendering) without any API keys or
network access:

```bash
python3 examples/scripted_demo.py
```

This mocks only the Groq chat-completion call (so it works with zero
setup); every other line of code that runs - tool execution, scoring,
route lookup, the flight demo estimate, the budget comparison, and the
CLI renderer - is the real, unmocked implementation. It shows two turns:

1. **"Plan a 5 day beach trip"** (no origin given) -> the agent asks
   where you're departing from instead of guessing.
2. Origin/date/travelers/budget supplied -> ranked destinations, each
   with a route, a demo flight estimate clearly labeled as such, and a
   flights-only budget verdict.

To see the identical flow with a **real** LLM choosing the tool calls,
add `GROQ_API_KEY` to `.env` and run `python3 main.py` instead - the
tool-calling and rendering code is exactly the same either way.

## Project layout

```
agent.py              Groq tool-calling loop, system prompt
tools.py              Tool functions the LLM can call; validates args,
                       orchestrates flight+budget on top of ranking
request_schema.py      Deterministic request validation
planner.py + scoring.py  Deterministic destination ranking
flight_service.py      Amadeus sandbox integration + demo fallback
budget.py              Deterministic flights-only budget math
currency_service.py    Live Frankfurter FX conversion
weather_service.py     Live WeatherAPI.com forecast
airports.py            Caribbean place-name -> IATA code lookup
config.py              Live/demo mode detection, setup messages
formatting.py          Shared CLI/Streamlit presentation helpers
main.py                CLI front end
streamlit_app.py        Streamlit front end (chat + adjustable filters)
data/destinations.json  Caribbean destination catalog + heuristic scores
data/routes.json        Seeded route coverage
tests/                  pytest suite (mocked HTTP, no live calls)
examples/scripted_demo.py  Reproducible end-to-end demo, no keys needed
```

## Limitations

- **Route coverage is thin.** `data/routes.json` only has ~10 seeded
  legs, mostly departing POS/GND/BGI. "Unknown" route status means the
  seed data doesn't cover it, not that no real route exists.
- **Destination preference scores are heuristic**, not derived from a
  real dataset. They're a reasonable-effort starting point for ranking
  logic, not a validated source of truth.
- **Amadeus's free tier is a TEST environment**: real API calls, but
  against limited/cached sample inventory, not production pricing. Many
  smaller Caribbean routes may return `no_results` there even though the
  route exists in reality.
- **No accommodation, food, transport, or activity pricing.** Every
  budget comparison says this explicitly rather than implying a full
  trip-cost estimate.
- **No persistence.** Conversation history lives only in memory for the
  running process/session.
- This project intentionally does not use LangGraph/CrewAI/AutoGPT -
  the tool-calling loop is a plain, explicit Python loop in `agent.py`,
  which is enough for a small, fixed toolset and is easier to reason
  about and debug.

## What would need more work before this is a real product

- Broader, licensed route/schedule data (or a GDS schedule API) instead
  of the seeded `routes.json`.
- A validated way to derive destination preference scores (e.g. from
  aggregated review data) instead of hand-set heuristics.
- Hotel/accommodation pricing, to make the budget check trip-level
  instead of flights-only.
- Amadeus production access (a business relationship, not a free
  signup) for real live fares, if this ever left prototype status.
