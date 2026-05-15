# Travel Planner AI

A conversational AI travel assistant that creates personalised day-by-day
itineraries with real place names, estimates trip budgets, provides weather
forecasts, and shares destination-specific travel tips — for any city
in the world.

Built with Python, LangChain, and Streamlit. Powered by Groq (Llama 3.3).

**Live demo:** [your-deployed-url.streamlit.app](https://your-deployed-url.streamlit.app)

---

## For Users — How to Use the App

1. Open the link above in your browser
2. Click the **Register** tab and create an account (username + password)
3. Switch to the **Login** tab and sign in
4. Start chatting! Try something like:
   - "Plan a 5-day mid-range trip to Rome"
   - "What is the weather like in Tokyo in April?"
   - "Estimate budget for 2 people, 7 days in Barcelona"
5. Click **Export this plan to PDF** to download your itinerary
6. Expand **Google Maps links** to see clickable map links for every activity
7. You get **10 messages per day** — the counter resets at midnight

No installation, no API keys, no technical knowledge needed. Just open the
link and start planning your trip.

---

## Features

- Day-by-day itineraries with real restaurants, museums, and attractions
- Google Maps links for every activity
- Budget estimates with real hotel recommendations
- Weather forecasts with packing advice
- Trip profile that remembers your preferences
- PDF export per trip
- User authentication (signup/login)
- Daily usage limit (10 messages per user)
- Server-side API key (users don't need their own)

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

    Budget Estimate (1 person, 3 nights, mid-range):
      Accommodation:   $390  (Hotel Electra Metropolis, Syntagma)
      Local transport:  $60
      Food & dining:   $150
      Activities:       $90
      Miscellaneous:    $55
      TOTAL:           $745

    Would you like destination tips or weather info for Athens?

    ---

    You: What is the weather like in Athens in April?

    [Tool called: get_weather_summary]

    Assistant:
    April in Athens is excellent! Expect 11-20 C with low rainfall.
    Pack light layers, sunscreen, and comfortable walking shoes.
    It is one of the best months to visit — warm but not yet crowded.

---

## For Developers — Local Setup

### Step 1 — Get a free Groq API key

1. Go to https://console.groq.com
2. Sign up (completely free, no credit card)
3. Create an API Key and copy it

### Step 2 — Clone and install

    git clone https://github.com/YOUR_USERNAME/travel-planner.git
    cd travel-planner
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

### Step 3 — Configure your API key

Create the secrets file:

    mkdir -p .streamlit
    echo 'GROQ_API_KEY = "gsk_...your_key"' > .streamlit/secrets.toml

Or use a .env file:

    echo 'GROQ_API_KEY=gsk_...your_key' > .env

### Step 4 — Run locally

    streamlit run interface/app.py

Open http://localhost:8501, register an account, and start chatting.

---

## Project Structure

    travel_chatbot/
        .streamlit/
            secrets.toml          # API key (gitignored)
        core/
            __init__.py
            chatbot.py            # LangChain agent + trip profile
        tools/
            __init__.py
            travel_tools.py       # Four AI-powered tool functions
        interface/
            __init__.py
            app.py                # Streamlit UI + auth + rate limiting
        config.yaml               # User credentials (auto-created)
        usage.db                  # Usage tracking (auto-created, gitignored)
        cli.py                    # Command-line interface
        requirements.txt
        .gitignore
        README.md

---

## Tool Functions

| Tool                  | What it does                                         |
|-----------------------|------------------------------------------------------|
| generate_itinerary    | Day-by-day plan with real places + Google Maps links  |
| estimate_budget       | Cost breakdown with real hotel recommendation         |
| get_destination_tips  | Currency, transport, safety, food, etiquette tips     |
| get_weather_summary   | Temperature, rainfall, packing advice for any month   |

---

## Model Used

**Llama 3.3 70B Versatile** (main agent) and **Llama 3.1 8B Instant**
(internal tool recommendations), both via Groq's free API.

---

## Deploy to Streamlit Community Cloud

1. Push your code to GitHub
2. Go to https://share.streamlit.io and sign in with GitHub
3. Click New app, select your repo
4. Set main file path to: interface/app.py
5. In Advanced settings > Secrets, paste:
       GROQ_API_KEY = "gsk_...your_actual_key"
6. Click Deploy
7. Share the URL with anyone

---

## Architecture

    User (browser)
        |
        v
    Streamlit Cloud (app.py)
        |--- Authentication (streamlit-authenticator)
        |--- Rate limiting (SQLite, 10 msgs/day)
        |
        v
    LangChain Agent (Llama 3.3 via Groq)
        |--- decides which tools to call
        v
    Tool Functions (travel_tools.py)
        |--- internal LLM calls (Llama 3.1 8B)
        |--- returns structured JSON
        v
    Agent formats response
        |--- Google Maps links
        |--- PDF export
        v
    User sees the itinerary