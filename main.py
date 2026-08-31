from agent import run_agent


def print_recommendation(rank, result):
    cost = result["cost_breakdown"]
    score = result["score_breakdown"]

    medal = ["🥇", "🥈", "🥉"][rank - 1] if rank <= 3 else f"{rank}."

    print(f"\n{medal} {result['name']} ({result['airport']})")
    print(f"WeyWeGoing Score: {score['final_score']} / 100")
    print(f"  (budget fit: {score['budget_fit']} | preference match: {score['preference_match']})")
    print(f"\n  ✈ Flight        TT${cost['flight']}")
    print(f"  🏨 Accommodation TT${cost['accommodation']}")
    print(f"  🍛 Food          TT${cost['food']}")
    print(f"  🚕 Transport     TT${cost['transport']}")
    print(f"  🎉 Activities    TT${cost['activities']}")
    print(f"  ─────────────────────────")
    print(f"  Estimated Total  TT${cost['total']}")
    print(f"  Remaining buffer TT${result['buffer_remaining']}")


def print_destination_details(destination):
    print(f"\n📍 {destination['name']} ({destination['airport']})")
    print(f"  Estimated flight: TT${destination['estimated_flight_ttd']}")
    print(f"  Ideal trip length: {destination['recommended_trip_length']['ideal_days']} days")
    print("  Scores (0-10):")
    for category, value in destination["scores"].items():
        print(f"    {category}: {value}")


def render_tool_trace(tool_calls):
    """
    Prints the structured data behind whatever the LLM just said, so
    you can see the tool-calling actually happened -- not just trust
    the model's prose. Useful for demos and for sanity-checking.
    """
    for call in tool_calls:
        print(f"\n[tool call: {call['name']}({call['arguments']})]")
        result = call["result"]

        if call["name"] == "recommend_destinations" and result.get("status") == "ok":
            for index, destination_result in enumerate(result["results"], start=1):
                print_recommendation(index, destination_result)
        elif call["name"] == "recommend_destinations" and result.get("status") == "no_matches":
            print("  -> no destinations fit that budget/duration")
        elif call["name"] == "get_destination_details" and result.get("status") == "ok":
            print_destination_details(result["destination"])
        elif result.get("status") in ("not_found", "error"):
            print(f"  -> {result.get('message', 'tool error')}")


def main():
    print("\nWeyWeGoing? 🌴✈️\n")
    print("Ask about a trip, or ask about a specific destination. Type 'quit' to exit.\n")

    conversation_history = None

    while True:
        user_message = input("> ")
        if user_message.strip().lower() in ("quit", "exit"):
            break

        outcome = run_agent(user_message, conversation_history)
        conversation_history = outcome["messages"]

        if outcome["tool_calls"]:
            render_tool_trace(outcome["tool_calls"])

        print(f"\n{outcome['reply']}\n")


if __name__ == "__main__":
    main()