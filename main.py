from agent import run_agent


def print_recommendation(rank, result):
    cost = result["cost_breakdown"]
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
        f"WeyWeGoing Score: "
        f"{score['final_score']} / 100"
    )

    print(
        f"  (budget fit: {score['budget_fit']} | "
        f"preference match: "
        f"{score['preference_match']})"
    )

    print(f"\n  ✈ Flight         TT${cost['flight']}")
    print(f"  🏨 Accommodation TT${cost['accommodation']}")
    print(f"  🍛 Food           TT${cost['food']}")
    print(f"  🚕 Transport      TT${cost['transport']}")
    print(f"  🎉 Activities     TT${cost['activities']}")
    print("  ─────────────────────────")
    print(f"  Estimated Total  TT${cost['total']}")
    print(
        f"  Remaining buffer "
        f"TT${result['buffer_remaining']}"
    )


def print_destination_details(destination):
    print(
        f"\n📍 {destination['name']} "
        f"({destination['airport']})"
    )

    print(
        f"  Local currency: "
        f"{destination['currency']}"
    )

    print(
        f"  Estimated flight: "
        f"TT${destination['estimated_flight_ttd']}"
    )

    print(
        f"  Ideal trip length: "
        f"{destination['recommended_trip_length']['ideal_days']} "
        f"days"
    )

    print("  Scores (0-10):")

    for category, value in destination["scores"].items():
        print(f"    {category}: {value}")


def render_tool_trace(tool_calls):
    """Prints the structured result behind each LLM tool call."""
    for call in tool_calls:
        print(
            f"\n[tool call: "
            f"{call['name']}({call['arguments']})]"
        )

        result = call["result"]

        if (
            call["name"] == "recommend_destinations"
            and result.get("status") == "ok"
        ):
            for index, destination_result in enumerate(
                result["results"],
                start=1
            ):
                print_recommendation(
                    index,
                    destination_result
                )

        elif (
            call["name"] == "recommend_destinations"
            and result.get("status") == "no_matches"
        ):
            print(
                "  -> no destinations fit "
                "that budget/duration"
            )

        elif (
            call["name"] == "get_destination_details"
            and result.get("status") == "ok"
        ):
            print_destination_details(
                result["destination"]
            )

        elif (
            call["name"] == "check_route"
            and result.get("status") == "ok"
        ):
            print(
                f"  Route type: "
                f"{result['route_type']}"
            )

            if result["route_type"] == "direct":
                for route in result["routes"]:
                    print(
                        f"  {route['origin']} -> "
                        f"{route['destination']} "
                        f"with {route['airline']}"
                    )

            else:
                print(
                    f"  Connection: "
                    f"{result['connection']}"
                )

        elif (
            call["name"] == "get_weather"
            and result.get("status") == "ok"
        ):
            weather = result["weather"]

            print(
                f"  Typical temperature: "
                f"{weather['average_temp_c']}°C"
            )

            print(
                f"  Rain risk: "
                f"{weather['rain_risk']}"
            )

            print(
                f"  Beach suitability: "
                f"{weather['beach_suitability']}"
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
    print("\nWeyWeGoing? 🌴✈️\n")

    print(
        "Ask about a trip, route, weather, "
        "currency, or destination."
    )

    print("Type 'quit' to exit.\n")

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

        conversation_history = outcome["messages"]

        if outcome["tool_calls"]:
            render_tool_trace(
                outcome["tool_calls"]
            )

        print(f"\n{outcome['reply']}\n")


if __name__ == "__main__":
    main()
