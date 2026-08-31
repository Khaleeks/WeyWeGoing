# WeyWeGoing? 🌴✈️

An AI travel intelligence agent for Caribbean trip planning.

Describe your trip in plain language — budget, time, interests, routes,
weather, or currency — and WeyWeGoing? decides which tools it needs to
answer you.

> "I have TT$3500 and a long weekend. Somewhere with beach and nightlife."

## Current tools

The Groq LLM can choose between:

- `recommend_destinations`
- `get_destination_details`
- `check_route`
- `get_weather`
- `convert_currency`

The LLM chooses the tool. Plain Python runs the tool and reads the data.

## Current data

This version uses **seeded demo data**, not live travel information:

```text
data/
  destinations.json
  routes.json
  weather.json
  currency.json
```

The fake data is intentional for prototyping the architecture. The next
major milestone is replacing each seeded source with a real API while
keeping the same tool interface.

For example:

```text
get_weather
    today -> weather.json
    later -> live weather API
```

The agent still calls the same tool.

## Architecture

```text
User
  ↓
agent.py
  ↓
LLM chooses tool
  ↓
tools.py
  ├── recommend_destinations -> planner.py -> destinations.json
  ├── get_destination_details -> destinations.json
  ├── check_route -> routes.json
  ├── get_weather -> weather.json
  └── convert_currency -> currency.json
```

`scoring.py` remains deterministic. The LLM does not create the
WeyWeGoing Score.

## Quickstart

```bash
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Add your Groq API key to `.env`:

```text
GROQ_API_KEY=your_key_here
```

## Good test prompts

```text
I have TT$3500 and 3 days. I want beaches and nightlife.

Tell me more about Grenada.

Can I get from Trinidad to Dominica?

What is the weather usually like in Barbados in February?

Convert 1000 TTD to BBD.
```

## Important limitation

All destination costs, route information, weather patterns, and exchange
rates in this version are seeded demo values. They are shaped like the
real data the product will eventually use, but they should not be treated
as current travel information.

## Next steps

- [x] Tool-calling agent
- [x] Seeded destination data
- [x] Seeded route data + route tool
- [x] Seeded weather data + weather tool
- [x] Seeded currency data + currency tool
- [ ] Make route convenience affect the WeyWeGoing Score
- [ ] Make weather affect the WeyWeGoing Score
- [ ] Replace seeded weather with a live weather API
- [ ] Replace seeded currency with a live FX API
- [ ] Replace seeded routes/prices with real aviation data
- [ ] Add eval suite
- [ ] Add FastAPI backend
- [ ] Add web frontend
- [ ] Add Route Radar
