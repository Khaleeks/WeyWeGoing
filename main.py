from agent import extract_preferences
from planner import recommend_destinations


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


def main():
    print("\nWeyWeGoing? 🌴✈️\n")

    user_message = input("Tell me what kind of trip you're looking for:\n> ")

    preferences = extract_preferences(user_message)

    print("\nI understood:")
    print(preferences)

    budget = preferences["budget"]
    if budget is None:
        budget = int(input("\nWhat's your budget in TTD? "))

    days = preferences["days"]
    if days is None:
        days = int(input("How many days are you travelling? "))

    results = recommend_destinations(
        budget=budget,
        days=days,
        preferences=preferences.get("preferences", {}),
    )

    print("\n" + "=" * 40)
    print("WeyWeGoing recommends:")
    print("=" * 40)

    if not results:
        print("\nNothing fitting that trip yet 😭 Try a higher budget or fewer days.")
    else:
        for index, result in enumerate(results, start=1):
            print_recommendation(index, result)

    print()


if __name__ == "__main__":
    main()
