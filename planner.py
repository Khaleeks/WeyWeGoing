import json


def load_destinations():
    with open("data/destinations.json", "r") as file:
        return json.load(file)


def calculate_trip_cost(destination, days):
    return (
        destination["estimated_flight_ttd"]
        + destination["daily_cost_ttd"] * days
    )


def recommend_destinations(budget, days, wants_beach=True, wants_nightlife=True):
    destinations = load_destinations()

    results = []

    for destination in destinations:
        total_cost = calculate_trip_cost(destination, days)

        if total_cost > budget:
            continue

        score = 0

        if wants_beach:
            score += destination["beach_score"]

        if wants_nightlife:
            score += destination["nightlife_score"]

        results.append({
            "name": destination["name"],
            "cost": total_cost,
            "score": score
        })

    return sorted(
        results,
        key=lambda x: x["score"],
        reverse=True
    )