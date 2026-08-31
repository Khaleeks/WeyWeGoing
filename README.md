# WeyWeGoing? 🌴✈️

An AI travel intelligence agent for Caribbean trip planning. Instead of
searching flights and hotels separately, you describe your trip in plain
language — budget, time, what you want to do — and WeyWeGoing? works out
which destinations are actually realistic, with an itemized cost
breakdown and an explainable match score.

> "I have TT$3500 and a long weekend. Somewhere with beach and nightlife."

## Why this isn't just a ChatGPT wrapper

The LLM is only used for one thing: turning a sentence into structured
preferences (`budget`, `days`, `preferences: {beach: 0.9, ...}`). Every
downstream decision — cost calculation, filtering by budget, and the
**WeyWeGoing Score** that ranks destinations — is plain, deterministic
Python in `planner.py` and `scoring.py`. The AI explains and interprets;
it doesn't invent the numbers. That separation is what makes the
recommendations testable and explainable rather than a black box.

## Runs on Groq

`agent.py` calls Groq's LLM API (`llama-3.3-70b-versatile`) to turn a
sentence into structured preferences. A `GROQ_API_KEY` is required —
there's no offline fallback, since the point of this project is to
demonstrate real LLM/agent integration rather than route around it.

## Quickstart

```bash
pip install -r requirements.txt
cp .env   # add your GROQ_API_KEY
python main.py
```

## Current architecture

```text
main.py        — CLI entry point, formats the recommendation output
agent.py       — natural language -> structured preferences (Groq LLM)
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

- [ ] `routes.json` — model Trinidad's actual Caribbean connections as a
      graph, so "cheapest route" vs "fewest connections" is a real
      pathfinding problem, not a flat list
- [ ] Live weather as the first real external tool call, feeding into
      the score
- [ ] Swap seeded destination costs for a real flights/hotels API
- [ ] Tool-call tracing: show *which* tools the agent called and why,
      not just the final answer
- [ ] Eval suite (`evals/`): a test set of example queries checking
      budget compliance, valid-route rate, and whether recommendations
      stay grounded in the underlying data rather than the LLM's guess
- [ ] FastAPI backend + simple web frontend
- [ ] Route Radar (tracks new/changing Caribbean flight routes) — later,
      after the core loop is solid

## Example output

```text
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
```
