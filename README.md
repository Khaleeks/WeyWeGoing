# WeyWeGoing? 🌴✈️

An AI-powered Caribbean travel intelligence agent.

WeyWeGoing? uses an LLM to understand natural-language travel requests
and choose tools. Python handles deterministic costs, routes, scoring,
weather data retrieval, and currency conversion.

## Current architecture

```text
User
  ↓
Groq LLM agent
  ↓
Tools
  ├── recommend_destinations
  ├── get_destination_details
  ├── check_route
  ├── get_weather
  └── convert_currency
  ↓
Planner + scoring
```

## Current data sources

### Real

- Weather: WeatherAPI.com

### Seeded demo data

- `data/destinations.json`
- `data/routes.json`
- `data/currency.json`

`data/weather.json` has been removed.

## Weather integration

WeatherAPI.com is called through:

```text
weather_service.py
```

The project reuses the airport codes already stored in
`destinations.json`.

Example:

```text
Grenada
  ↓
GND
  ↓
iata:GND
  ↓
WeatherAPI.com
```

No latitude/longitude table is needed.

The free WeatherAPI plan supports a 3-day forecast, so WeyWeGoing?
currently uses real weather in ranking only when the user provides an
exact travel date that appears in the returned forecast.

If no exact date is provided, or the date is outside the available
forecast window, weather receives a neutral score of 60.

## WeyWeGoing Score

Current prototype heuristic weights:

```text
Budget fit          25%
Preference match    40%
Route convenience   20%
Weather fit         15%
```

These weights are product assumptions for V1 and should later be
validated through evaluation and user testing.

### Route score

```text
Direct route   100
One stop        70
No route         0
```

Destinations without a reachable seeded route are filtered out before
ranking.

### Weather score

Weather uses real WeatherAPI forecast data.

The current simple heuristic uses chance of rain:

```text
0-20% rain     100
21-40%          85
41-60%          65
61-80%          45
81-100%         25
```

If no usable forecast is available:

```text
Weather score = 60
```

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.env`:

```text
GROQ_API_KEY=your_groq_api_key
WEATHER_API_KEY=your_weatherapi_key
```

Run:

```bash
python3 main.py
```

## Example weather prompts

```text
What's the weather in Grenada?
What's the 3-day forecast for Barbados?
What's Tobago's weather like right now?
```

## Example recommendation prompts

Without an exact date:

```text
I have TT$5000 and 4 days.
I want nature and adventure.
```

Weather stays neutral.

With an exact near-term date:

```text
I have TT$5000 and 3 days starting 2026-09-01.
I want beaches and nightlife.
```

If that date appears inside WeatherAPI's available forecast, real weather
affects the ranking.

## Roadmap

- [x] Tool-calling agent
- [x] Seeded destination profiles
- [x] Seeded route checking
- [x] Seeded currency conversion
- [x] Explainable destination ranking
- [x] Replace `weather.json` with WeatherAPI.com
- [ ] Replace `currency.json` with live FX API
- [ ] Replace `routes.json` with live flight/route data
- [ ] Replace seeded destination costs with real data
- [ ] Validate destination preference scores
- [ ] Add evaluation suite
- [ ] FastAPI backend
- [ ] Web frontend
- [ ] Route Radar
