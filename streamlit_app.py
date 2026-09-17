"""
streamlit_app.py

Streamlit front end for WeyWeGoing?.

Two ways in, both hitting the exact same deterministic tools:
- Chat: natural language -> agent.run_agent (LLM interprets + calls tools).
- Sidebar filters: a form that calls tools.recommend_destinations_tool
  directly, so ranking/budget/flights work even without a GROQ key, and
  so a user can adjust preferences without re-typing a sentence.

Run with: streamlit run streamlit_app.py
"""

import streamlit as st

import config
from agent import run_agent
from formatting import budget_line, flight_headline, missing_info_questions
from tools import recommend_destinations_tool

st.set_page_config(page_title="WeyWeGoing?", page_icon="🌴")

PREFERENCE_CATEGORIES = [
    "beach", "nightlife", "food", "culture",
    "nature", "romantic", "adventure", "relaxation",
]


def _provider_badge(name, mode):
    colors = {
        "live": "🟢",
        "sandbox": "🟡",
        "demo": "🟠",
        "unavailable": "🔴",
    }
    return f"{colors.get(mode, '⚪')} {name}: **{mode}**"


def render_status_sidebar():
    status = config.status_summary()

    st.sidebar.subheader("Provider status")
    st.sidebar.markdown(_provider_badge("Agent (Groq)", status["llm"]["mode"]))
    st.sidebar.markdown(
        _provider_badge("Weather (WeatherAPI)", status["weather"]["mode"])
    )
    st.sidebar.markdown(
        _provider_badge("Flights (Amadeus)", status["flights"]["mode"])
    )
    st.sidebar.markdown(
        _provider_badge("Currency (Frankfurter)", status["currency"]["mode"])
    )

    for key in ("llm", "weather", "flights"):
        if status[key]["message"]:
            with st.sidebar.expander(f"Set up {key} live mode"):
                st.write(status[key]["message"])


def render_destination_card(rank, result):
    score = result["score_breakdown"]

    with st.container(border=True):
        st.markdown(
            f"### {rank}. {result['name']} ({result['airport']})"
        )
        st.caption(f"{result['region_type']} - currency {result['currency']}")

        cols = st.columns(4)
        cols[0].metric("WeyWeGoing Score", f"{score['final_score']}/100")
        cols[1].metric("Preference match", f"{score['preference_match']}")
        cols[2].metric("Route", f"{score['route_convenience']}")
        cols[3].metric("Weather", f"{score['weather_fit']}")

        route = result["route"]

        if route["route_type"] == "direct":
            leg = route["legs"][0]
            st.write(
                f"✈ Route: {leg['origin']} → {leg['destination']} "
                f"(direct, {leg['airline']})"
            )
        elif route["route_type"] == "one_stop":
            st.write(
                f"✈ Route: {route['legs'][0]['origin']} → "
                f"{route['connection']} → {route['legs'][1]['destination']}"
            )
        else:
            st.write("✈ Route: not covered by the current seeded route data")

        if result.get("weather"):
            weather = result["weather"]
            st.write(
                f"☀ {weather['condition']}, {weather['average_temp_c']}°C "
                f"avg, {weather['rain_probability']}% rain"
            )

        st.write(flight_headline(result.get("flight")))

        summary = budget_line(result.get("budget_evaluation"))

        if summary:
            fits = result["budget_evaluation"]["within_budget_for_flights_only"]
            (st.success if fits else st.warning)(summary)


def render_recommend_result(result):
    if result["status"] == "missing_info":
        st.warning("I need a bit more information:")

        for question in missing_info_questions(result["missing_fields"]):
            st.write(f"- {question}")

        return

    if result["status"] == "invalid_request":
        st.error("That request has a problem:")

        for message in result["errors"]:
            st.write(f"- {message}")

        return

    if result["status"] == "no_matches":
        st.info("No destinations matched.")
        return

    st.caption(
        f"Trip: {result['days']} day(s), {result['travelers']} "
        f"traveler(s), from {result['origin']}. Quotes refreshed just "
        "now - prices and availability can change."
    )

    for index, destination_result in enumerate(result["results"], start=1):
        render_destination_card(index, destination_result)


def render_tool_call(call):
    with st.expander(
        f"🔧 {call['name']}({call['arguments']})", expanded=False
    ):
        if call["name"] == "recommend_destinations":
            render_recommend_result(call["result"])
        else:
            st.json(call["result"])


def chat_tab():
    if "messages" not in st.session_state:
        st.session_state.messages = None

    if "history" not in st.session_state:
        st.session_state.history = []

    for entry in st.session_state.history:
        with st.chat_message(entry["role"]):
            st.write(entry["content"])

            for call in entry.get("tool_calls", []):
                render_tool_call(call)

    user_message = st.chat_input(
        "Describe your trip: where from, when, budget, preferences..."
    )

    if user_message:
        st.session_state.history.append({
            "role": "user",
            "content": user_message,
        })

        with st.chat_message("user"):
            st.write(user_message)

        outcome = run_agent(user_message, st.session_state.messages)
        st.session_state.messages = outcome["messages"]

        with st.chat_message("assistant"):
            for call in outcome["tool_calls"]:
                render_tool_call(call)

            st.write(outcome["reply"])

        st.session_state.history.append({
            "role": "assistant",
            "content": outcome["reply"],
            "tool_calls": outcome["tool_calls"],
        })


def filters_tab():
    st.write(
        "Adjust these directly - this path calls the same deterministic "
        "ranking/flight/budget code as the chat, without needing the LLM."
    )

    with st.form("filters_form"):
        col1, col2 = st.columns(2)

        origin = col1.text_input("Departing from", value="Trinidad")
        days = col2.number_input("Trip length (days)", min_value=1, value=5)

        travel_date = col1.text_input(
            "Travel date (YYYY-MM-DD, optional)", value=""
        )
        travelers = col2.number_input("Travelers", min_value=1, value=1)

        budget_amount = col1.number_input(
            "Budget (optional, 0 = none)", min_value=0.0, value=0.0
        )
        budget_currency = col2.text_input("Budget currency", value="USD")

        budget_scope = st.radio(
            "Budget is...", ["per_person", "group"], horizontal=True
        )

        st.write("Preferences (0 = don't care, 1 = very important)")
        pref_cols = st.columns(4)
        preferences = {}

        for index, category in enumerate(PREFERENCE_CATEGORIES):
            with pref_cols[index % 4]:
                preferences[category] = st.slider(
                    category.capitalize(), 0.0, 1.0, 0.0, 0.1
                )

        submitted = st.form_submit_button("Get recommendations")

    if submitted:
        active_preferences = {
            category: weight
            for category, weight in preferences.items()
            if weight > 0
        }

        result = recommend_destinations_tool(
            days=int(days),
            origin=origin,
            travel_date=travel_date or None,
            travelers=int(travelers),
            budget_amount=budget_amount or None,
            budget_currency=budget_currency,
            budget_scope=budget_scope if budget_amount else None,
            preferences=active_preferences,
        )

        render_recommend_result(result)


def main():
    st.title("WeyWeGoing? 🌴✈️")
    st.caption("AI-assisted Caribbean trip planning - transparent about costs.")

    render_status_sidebar()

    tab_chat, tab_filters = st.tabs(["💬 Chat", "🎚 Adjust filters"])

    with tab_chat:
        chat_tab()

    with tab_filters:
        filters_tab()


if __name__ == "__main__":
    main()
