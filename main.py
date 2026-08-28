from planner import recommend_destinations

print("\nWeyWeGoing? 🌴✈️\n")

budget = int(input("What's your budget in TTD? "))
days = int(input("How many days are you travelling? "))

beach_answer = input("You want beaches? (yes/no): ").lower()
nightlife_answer = input("You want nightlife? (yes/no): ").lower()

wants_beach = beach_answer == "yes"
wants_nightlife = nightlife_answer == "yes"

results = recommend_destinations(
    budget=budget,
    days=days,
    wants_beach=wants_beach,
    wants_nightlife=wants_nightlife
)

print("\nWeyWeGoing recommends:\n")

if not results:
    print("Nothing fitting that budget yet 😭")
else:
    for index, result in enumerate(results, start=1):
        print(
            f"{index}. {result['name']} "
            f"- TT${result['cost']} "
            f"- score: {result['score']}"
        )