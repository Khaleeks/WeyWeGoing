from agent import run_agent


def print_route(route):
    """Prints route information used in ranking."""
    if route["route_type"] == "direct":
        leg = route["legs"][0]

        print(
            f"  🛫 Route          "
            f"{leg['origin']} -> "
            f"{leg['destination']} "
            "(direct)"
        )

    elif route["route_type"] == "one_stop":
        legs = route["legs"]

        print(
            f"  🛫 Route          "
            f"{legs[0]['origin']} -> "
            f"{route['connection']} -> "
            f"{legs[1]['destination']}"
        )

    else:
        print(
            "  🛫 Route          "
            "not covered by current route data"
        )


def print_recommendation(rank, result):
    score = result["score_breakdown"]

    medal = (
        ["🥇", "🥈", "🥉"][rank - 1]
        if rank <= 3
        else f"{rank}."
    )

    print(
        f"\n{medal} {result['name']} "
        f"({result['airport']})"
    )

    print(
        f"  {result['region_type']}"
    )

    print(
        f"  Currency: {result['currency']}"
    )

    print(
        f"\nWeyWeGoing Score: "
        f"{score['final_score']} / 100"
    )

    print(
        f"  Preference match:  "
        f"{score['preference_match']}"
    )

    print(
        f"  Route convenience: "
        f"{score['route_convenience']}"
    )

    print(
        f"  Weather fit:       "
        f"{score['weather_fit']}"
    )

    print_route(result["route"])

    if result["weather"]:
        weather = result["weather"]

        print(
            f"  ☀ Weather         "
            f"{weather['condition']}, "
            f"{weather['average_temp_c']}°C avg, "
            f"{weather['rain_probability']}% rain"
        )

    elif result["travel_date"]:
        print(
            "  ☀ Weather         "
            "forecast unavailable for that date"
        )

    else:
        print(
            "  ☀ Weather         "
            "not included (no exact date provided)"
        )


def print_destination_details(destination):
    print(
        f"\n📍 {destination['name']} "
        f"({destination['airport']})"
    )

    print(
        f"  Country/area: "
        f"{destination['country']}"
    )

    print(
        f"  Region type: "
        f"{destination['region_type']}"
    )

    print(
        f"  Country code: "
        f"{destination['country_code']}"
    )

    print(
        f"  Currency: "
        f"{destination['currency']}"
    )

    print("  Preference scores (0-10):")

    for category, value in (
        destination["scores"].items()
    ):
        print(
            f"    {category}: {value}"
        )


def render_tool_trace(tool_calls):
    """Prints the structured result behind each LLM tool call."""
    for call in tool_calls:
        print(
            f"\n[tool call: "
            f"{call['name']}("
            f"{call['arguments']})]"
        )

        result = call["result"]

        if (
            call["name"]
            == "recommend_destinations"
            and result.get("status") == "ok"
        ):
            if result.get("budget") is not None:
                print(
                    "  Budget noted, but not yet evaluated "
                    "(real pricing API not connected)."
                )

            for index, destination_result in enumerate(
                result["results"],
                start=1
            ):
                print_recommendation(
                    index,
                    destination_result
                )

        elif (
            call["name"]
            == "recommend_destinations"
            and result.get("status")
            == "no_matches"
        ):
            print(
                "  -> no destinations found"
            )

        elif (
            call["name"]
            == "get_destination_details"
            and result.get("status") == "ok"
        ):
            print_destination_details(
                result["destination"]
            )

        elif (
            call["name"]
            == "check_route"
            and result.get("status") == "ok"
        ):
            print(
                f"  Route type: "
                f"{result['route_type']}"
            )

            if result["route_type"] == "direct":
                leg = result["legs"][0]

                print(
                    f"  {leg['origin']} -> "
                    f"{leg['destination']} "
                    f"with {leg['airline']}"
                )

            else:
                print(
                    f"  Connection: "
                    f"{result['connection']}"
                )

        elif (
            call["name"] == "check_route"
            and result.get("status") == "unknown"
        ):
            print(
                f"  -> {result['message']}"
            )

        elif (
            call["name"] == "get_weather"
            and result.get("status") == "ok"
        ):
            print(
                f"  Live forecast for "
                f"{result['destination']}:"
            )

            for day in result["forecast"]:
                print(
                    f"    {day['date']}: "
                    f"{day['condition']}, "
                    f"{day['average_temp_c']}°C avg, "
                    f"{day['rain_probability']}% rain"
                )

        elif (
            call["name"] == "convert_currency"
            and result.get("status") == "ok"
        ):
            print(
                f"  {result['amount']} "
                f"{result['from_currency']} "
                f"≈ {result['converted_amount']} "
                f"{result['to_currency']}"
            )

        elif result.get("status") in (
            "not_found",
            "error"
        ):
            print(
                f"  -> "
                f"{result.get('message', 'tool error')}"
            )


def main():
    print(
        "\nWeyWeGoing? 🌴✈️\n"
    )

    print(
        "Ask about a Caribbean trip, route, "
        "weather, currency, or destination."
    )

    print(
        "Type 'quit' to exit.\n"
    )

    conversation_history = None

    while True:
        user_message = input("> ")

        if user_message.strip().lower() in (
            "quit",
            "exit"
        ):
            break

        outcome = run_agent(
            user_message,
            conversation_history
        )

        conversation_history = (
            outcome["messages"]
        )

        if outcome["tool_calls"]:
            render_tool_trace(
                outcome["tool_calls"]
            )

        print(
            f"\n{outcome['reply']}\n"
        )


if __name__ == "__main__":
    main()
