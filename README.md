# Travel Planner AI

A conversational AI travel assistant built with **Python** and **LangChain**,
powered by **Groq** (Llama 3.3 70B). The assistant creates personalised
day-by-day itineraries with real place names and Google Maps links, estimates
trip budgets with real hotel recommendations, provides weather forecasts,
and shares destination-specific travel tips — all through structured
LLM-powered tool calls.

The tool functions use an internal AI recommendation engine that generates
fresh, location-specific results for **any city in the world**, every time.

---

## Project Structure

    travel_chatbot/
        core/
            __init__.py
            chatbot.py            # LangChain agent, conversation logic, trip profile
        tools/
            __init__.py
            travel_tools.py       # Four AI-powered tool functions + maps helper
        interface/
            __init__.py
            app.py                # Streamlit web interface with PDF export
        cli.py                    # Command-line interface
        requirements.txt
        .env
        .gitignore
        README.md

---

## Model Used

**Llama 3.3 70B Versatile** via **Groq** (langchain-groq).

Groq provides a completely free API — no credit card, no billing, no trial period.
The model is used in two places:

1. **The main agent** — decides which tools to call and formats the final response.
2. **Inside the tool functions** — a smaller model (Llama 3.1 8B) generates real,
   location-specific recommendations for any city.

---

## Tool Functions

All tools are in tools/travel_tools.py using LangChain's @tool decorator.

| Tool                  | What it does                                         |
|-----------------------|------------------------------------------------------|
| generate_itinerary    | Day-by-day plan with real places + Google Maps links  |
| estimate_budget       | Cost breakdown with a real hotel recommendation       |
| get_destination_tips  | Currency, transport, safety, food, and etiquette tips |
| get_weather_summary   | Temperature, rainfall, packing advice for any month   |

Each tool calls the Groq LLM internally to generate location-specific data,
then returns structured JSON that the main agent formats for the user.

### Google Maps Integration

The generate_itinerary tool includes Google Maps search URLs for every activity.
A helper function `make_google_maps_link(query)` URL-encodes the place name
and returns a clickable Google Maps link. These links are visible in the tool
call expander in the Streamlit interface.

### Weather Summary

The get_weather_summary tool uses mock climate data for common destination types
(tropical, mediterranean, temperate, cold, desert) mapped to 50+ cities.
It returns temperature ranges, rainfall levels, packing advice, and travel
warnings for any month. No external API needed.

---

## Trip Profile Feature

The chatbot maintains a trip profile that automatically updates as the user
provides preferences (destination, budget, interests, travelers, etc.).
The profile is shown in the Streamlit sidebar and is reused across tool calls
so the user does not need to repeat information.

The profile resets when the conversation is cleared.

---

## Setup Instructions

### Step 1 — Get a free Groq API key

1. Go to https://console.groq.com
2. Sign up with Google or email (completely free, no credit card needed)
3. Go to API Keys, click Create API Key, and copy it

### Step 2 — Clone the repository

    git clone https://github.com/Anastasis97/travel-planner.git
    cd travel-planner

### Step 3 — Create a virtual environment

    python -m venv .venv

    # Mac / Linux:
    source .venv/bin/activate

    # Windows:
    .venv\Scripts\activate

### Step 4 — Install dependencies

    pip install -r requirements.txt

### Step 5 — Add your API key

    Create a .env file

Then open .env and paste your key:

    GROQ_API_KEY=gsk_...your_key_here

### Step 6 — Run the app

    streamlit run interface/app.py

Open http://localhost:8501 in your browser.

---

## Features

- Real place names for any city in the world (AI-generated, different every time)
- Google Maps links for every activity in the itinerary
- Weather forecasts with packing advice for any month
- Trip profile that remembers your preferences across the conversation
- PDF export per trip (download button appears after each plan)
- Tool call inspector (expandable panel showing raw tool inputs/outputs)
- Quick-start prompt buttons for common requests

---

## Example Conversation

    You: Plan a 3-day mid-range trip to Athens. I love food and culture.

    [Tool called: generate_itinerary]
    [Tool called: estimate_budget]

    Assistant:

    ### Day 1 — Ancient Wonders & Athenian Flavours
    - Morning: Visit the Acropolis and Parthenon — arrive early to beat the crowds
    - Afternoon: Lunch at Diporto Agoras — try the lamb stew. Then stroll through Plaka
    - Evening: Rooftop cocktails at A for Athens with direct Acropolis views

    ### Day 2 — Markets, Museums & Mezedes
    - Morning: Explore the National Archaeological Museum
    - Afternoon: Food tour through Varvakios Central Market — try loukoumades at Lukumades
    - Evening: Dinner at Tzitzikas kai Mermigas — order the grilled octopus

    ### Day 3 — Hidden Gems & Farewell Feast
    - Morning: Visit the Ancient Agora and Temple of Hephaestus
    - Afternoon: Walk through Monastiraki Flea Market and explore Psiri
    - Evening: Farewell dinner at Spondi in a romantic garden setting

    Budget: $745 total (Hotel Electra Metropolis, Syntagma, $130/night)

    ---

    You: What is the weather like in Athens in April?

    [Tool called: get_weather_summary]

    Assistant:
    April in Athens is excellent! Expect 11-20 C with low rainfall.
    Pack light layers, sunscreen, and comfortable walking shoes.

---

## Architecture

    User message
        |
        v
    LangChain Agent (Llama 3.3 via Groq)
        |--- decides which tools to call
        |--- remembers trip profile
        v
    Tool Functions (travel_tools.py)
        |--- each tool calls Groq LLM internally (Llama 3.1 8B)
        |--- generates real places, hotels, tips for ANY city
        |--- adds Google Maps links
        |--- returns structured JSON
        v
    Agent formats the JSON into a friendly response
        |
        v
    Streamlit UI / CLI displays the result
        |--- PDF export per trip
        |--- Trip profile in sidebar
        |--- Map links in tool expander

---