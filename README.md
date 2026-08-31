# WeyWeGoing? 🌴✈️

An AI travel intelligence agent for Caribbean trip planning.

WeyWeGoing? uses a tool-calling LLM for conversation, while plain Python
handles travel data, trip costs, route checking, currency conversion, and
the WeyWeGoing Score.

## Recommendation ranking

The recommendation engine now considers:

- 25% budget fit
- 40% destination preference match
- 20% route convenience
- 15% weather fit

Weather affects the score only when the user provides a travel month.
If no month is supplied, weather receives a neutral score.

A destination that has no direct or one-stop route in the seeded route
dataset is not recommended.

Currency does not receive a score. All trip costs are already normalized
to TTD, so adding a currency score would be arbitrary. Instead, WeyWeGoing?
converts the traveler's remaining TTD budget into the destination's local
currency to make the recommendation more useful.

## Data

All current data is SEEDED DEMO DATA:

```text
data/
  destinations.json
  routes.json
  weather.json
  currency.json
```

It is intended to test the architecture and will later be replaced with
live APIs or verified sources.

## Tools

- `recommend_destinations`
- `get_destination_details`
- `check_route`
- `get_weather`
- `convert_currency`

## Example

```text
> I have TT$4000 and 3 days in February.
> I want beaches and nightlife.
```

The recommendation tool now:

1. loads possible destinations
2. checks whether each destination is reachable from POS
3. filters destinations over budget
4. loads February weather
5. scores budget + interests + route + weather
6. converts the remaining TTD buffer into local currency
7. returns the top 3

## Quickstart

```bash
pip install -r requirements.txt
python main.py
```

`.env`:

```text
GROQ_API_KEY=your_key_here
```

## Roadmap

- [x] Tool-calling agent
- [x] Destination data
- [x] Route data + route checking
- [x] Weather data + weather tool
- [x] Currency data + currency conversion
- [x] Route convenience influences recommendation ranking
- [x] Weather influences recommendation ranking
- [x] Local-currency spending buffer shown with recommendations
- [ ] Replace seeded weather with live weather API
- [ ] Replace seeded currency with live FX API
- [ ] Replace seeded routes and prices with real aviation data
- [ ] Add agent evaluation suite
- [ ] FastAPI backend
- [ ] Web frontend
- [ ] Route Radar
