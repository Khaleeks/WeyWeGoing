# WeyWeGoing? 🌴✈️

An AI-powered Caribbean travel intelligence agent.

## Caribbean destination catalog

`data/destinations.json` is now the master list of Caribbean places
supported by WeyWeGoing?.

It contains only:

```text
name
country
country_code
airport
currency
region_type
scores
```

It no longer contains made-up flight prices, hotel prices, food costs,
transport costs, activity costs, or recommended trip lengths.

The preference scores are still temporary V1 heuristics and can be
validated or replaced later.

## Current real vs seeded data

### Real

- Weather → WeatherAPI.com

### Seeded / temporary

- Destination preference scores → `destinations.json`
- Route coverage → `routes.json`
- Currency exchange rates → `currency.json`

### Not connected yet

- Live flight prices
- Live hotel prices
- Real trip-cost estimates

Because real pricing is not connected yet, the system no longer claims
that a destination fits a user's budget.

A user can still provide a budget, and the agent keeps it as context, but
budget does not currently affect the numerical ranking.

## Current WeyWeGoing Score

```text
Preference match    60%
Route convenience   25%
Weather fit         15%
```

These weights are prototype heuristics.

Route scoring:

```text
Direct route      100
One stop           70
Unknown coverage   50
```

Unknown means `routes.json` does not currently contain enough data. It
does NOT mean the real route does not exist.

Weather scoring uses real WeatherAPI forecast data when an exact near-term
date is available. Otherwise weather receives a neutral score of 60.

## Architecture

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

## Setup

```bash
pip install -r requirements.txt
```

`.env`:

```text
GROQ_API_KEY=your_groq_api_key
WEATHER_API_KEY=your_weatherapi_key
```

Run:

```bash
python3 main.py
```

## Roadmap

- [x] Caribbean destination catalog
- [x] Tool-calling agent
- [x] WeatherAPI integration
- [x] Preference ranking
- [x] Route-aware ranking
- [ ] Replace `currency.json` with live FX API
- [ ] Replace `routes.json` with live route/flight API
- [ ] Add real flight pricing
- [ ] Add real accommodation pricing
- [ ] Reintroduce budget-fit scoring using real prices
- [ ] Validate destination preference scores
- [ ] Add evaluation suite
- [ ] FastAPI backend
- [ ] Web frontend
