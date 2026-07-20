# Travel Planner AI

A conversational AI travel assistant that creates rich, personalised day-by-day
itineraries with multiple real place suggestions, Google Maps links, budget
estimates, must-try foods, and hotel recommendations — for any city in the world.

Built with Python, LangChain, and Streamlit. Powered by Google Gemini 2.5 Flash,
with live DuckDuckGo web search for current recommendations.

**Live demo:** https://travel-planner-t5ogxfvvkurteqcmmqvuro.streamlit.app/

---

## For Users — How to Use the App

1. Open the link above in your browser
2. Click the **Register** tab and create an account (your email is your username)
3. Switch to the **Login** tab and sign in with your email — you stay signed in
   for 30 days on the same browser (password-less re-authentication cookie)
4. Start chatting! Try something like:
   - "Plan a 3-day trip to Lesvos island in Greece on a medium budget"
   - "Create a 5-day mid-range trip to Rome with lots of food and culture"
   - "What is the weather like in Tokyo in April?"
5. Click **Export this plan to PDF** to download your itinerary
6. All place names are clickable Google Maps links
7. You get **10 messages per day** — the counter resets at midnight

---

## Features

- **Live web search** — the agent searches travel blogs and guides before writing
  the plan, so suggestions are real and current
- Rich itineraries with **intro paragraph**, day-by-day plan, multiple suggestions per time slot
- **Google Maps links** on every place, restaurant, hotel, and attraction
- **Multiple restaurant options** per meal with specific dishes to order
- **Budget breakdown** with cost ranges per category
- **Must-try local foods** section with descriptions
- **Hotel recommendations** with price ranges and areas
- **Best areas to stay** guide
- Weather forecasts with packing advice
- Trip profile that remembers preferences
- PDF export per trip
- **Guaranteed complete responses** — a post-processing step checks that every
  itinerary includes the budget table, best areas, must-try foods, and hotels,
  and asks the model to fill in anything missing
- **Self-healing Google Maps links** — every link is validated and rebuilt from
  the place name after generation, so malformed URLs never reach the user
- User authentication (sign in with email, 30-day remember-me cookie) and daily usage limits

---

## Example Conversation

**User:** Hey, create me a 3-day trip plan to Lesvos island in Greece on a medium budget

**Assistant:**

Lesvos is perfect for a 3-day medium-budget trip — you can combine traditional
villages, amazing beaches, ouzo tavernas, and relaxed island vibes without spending
Santorini/Mykonos money. The best way to experience the island in a short time is
to split your days between Mytilene (capital), the north side around Molyvos/Petra,
and the southern beaches around Plomari. Renting a small car is highly recommended
because distances are long.

---

## Day 1 — Mytilene & Eastern Lesvos

### Morning
Arrive in Mytilene and walk through the harbor promenade and Ermou street. Visit:
- [Mytilene Castle](https://www.google.com/maps/search/Mytilene+Castle+Lesvos)
- [Old Harbor Area](https://www.google.com/maps/search/Old+Harbor+Mytilene+Lesvos)

For a quick swim close to town, head to
[Tsamakia Beach](https://www.google.com/maps/search/Tsamakia+Beach+Lesvos).

### Lunch
Try authentic Lesvos meze and seafood at:
- [Diavlos Traditional Tavern](https://www.google.com/maps/search/Diavlos+Mytilene+Lesvos) — try sardines from Kalloni with ouzo
- [Ermis Ouzeri](https://www.google.com/maps/search/Ermis+Ouzeri+Mytilene) — stuffed zucchini flowers and fresh octopus

### Afternoon
Drive to [Mantamados Monastery](https://www.google.com/maps/search/Mantamados+Monastery+Lesvos),
then continue toward Molyvos. Stop for photos in
[Petra village](https://www.google.com/maps/search/Petra+Village+Lesvos) on the way.

### Evening
Spend sunset in [Molyvos (Mithymna)](https://www.google.com/maps/search/Molyvos+Lesvos) —
stone alleys, castle views, and a romantic small harbor. Walk up to
[Molivos Castle](https://www.google.com/maps/search/Molivos+Castle+Lesvos) for panoramic views.
Dinner by the sea in the harbor area.

---

## Day 2 — Petra, Beaches & Eftalou

### Morning
Visit [Petra village](https://www.google.com/maps/search/Petra+Lesvos) and climb to
[Panagia Glykofilousa church](https://www.google.com/maps/search/Panagia+Glykofilousa+Petra+Lesvos)
on the rock. Then relax at
[Anaxos Beach](https://www.google.com/maps/search/Anaxos+Beach+Lesvos).

### Lunch
Seaside seafood lunch:
- [Captain's Table Molyvos](https://www.google.com/maps/search/Captains+Table+Molyvos+Lesvos) — grilled fresh fish
- [Taverna The Octopus](https://www.google.com/maps/search/Octopus+Taverna+Molyvos) — octopus in wine sauce

### Afternoon
Drive to [Eftalou Hot Springs](https://www.google.com/maps/search/Eftalou+Hot+Springs+Lesvos)
for a thermal bath. Then continue to
[Agios Isidoros Beach](https://www.google.com/maps/search/Agios+Isidoros+Beach+Lesvos) —
crystal-clear water, one of the best on the island.

### Evening
Ouzo evening by the harbor in Molyvos. Or return to Mytilene for bars and younger crowds.

---

## Day 3 — Plomari & Southern Lesvos

### Morning
Drive south to [Plomari](https://www.google.com/maps/search/Plomari+Lesvos), the ouzo capital.
Visit the [Barbayanni Ouzo Museum](https://www.google.com/maps/search/Barbayanni+Ouzo+Museum+Plomari).

### Beach Time
Relax at [Vatera Beach](https://www.google.com/maps/search/Vatera+Beach+Lesvos) —
one of the longest beaches in Greece.

### Lunch & Evening
Final seafood lunch in Plomari, then return to Mytilene for a farewell dinner at:
- [Olive Street Food](https://www.google.com/maps/search/Olive+Street+Food+Mytilene) — modern Greek street food
- [Refenes](https://www.google.com/maps/search/Refenes+Mytilene+Lesvos) — traditional dishes with sea view

---

## Suggested Budget (Mid-Range)
| Category | Approximate Cost |
|---|---|
| Hotel | EUR 70-120/night |
| Food | EUR 25-45/day |
| Car rental | EUR 35-55/day |
| Activities | EUR 10-20/day |
| Drinks & extras | EUR 20-40/day |

**Estimated total for 3 days:**
- Solo traveler: ~EUR 450-700
- Couple: ~EUR 700-1100

## Best Areas to Stay
- **Molyvos** — best overall atmosphere and beauty
- **Mytilene** — best for nightlife and convenience
- **Petra** — best relaxed beach vibe

## Must-Try Local Foods
- **Sardines from Kalloni** — famous throughout Greece, best grilled fresh
- **Lesvos ouzo** — the island produces Greece's finest ouzo
- **Ladotyri cheese** — PDO aged cheese preserved in olive oil
- **Fresh octopus** — grilled or in vinegar, a staple of every ouzeri
- **Stuffed zucchini flowers** — delicate and flavourful, a summer favourite
- **Local olive oil dishes** — Lesvos has 11 million olive trees

Lesvos is considered one of the best food islands in Greece thanks to its
seafood, olive oil, and meze culture.

## Hotel Suggestions
- [Olive Press Hotel](https://www.google.com/maps/search/Olive+Press+Hotel+Molyvos+Lesvos) — EUR 80-110/night, Molyvos
- [Hotel Molyvos I](https://www.google.com/maps/search/Hotel+Molyvos+I+Lesvos) — EUR 65-90/night, Molyvos
- [Loriet Hotel](https://www.google.com/maps/search/Loriet+Hotel+Mytilene+Lesvos) — EUR 70-100/night, Mytilene

---

## For Developers — Local Setup

### Step 1 — Get a free Google AI Studio (Gemini) API key

1. Go to https://aistudio.google.com
2. Sign in with any Google account (completely free, no credit card)
3. Click **Get API key** (key icon in the left sidebar, or visit
   https://aistudio.google.com/apikey directly)
4. Click **Create API key**, pick or auto-create a Google Cloud project,
   and copy the key (starts with `AIza...`)

Free tier: 250,000 tokens/minute and ~1,500 requests/day on Gemini 2.5 Flash —
roughly 30x the throughput of Groq's free tier, which this app previously used.

### Step 2 — Clone and install

    git clone https://github.com/YOUR_USERNAME/travel-planner.git
    cd travel-planner
    python -m venv .venv
    source .venv/bin/activate   # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

### Step 3 — Configure API key

    mkdir -p .streamlit
    echo 'GOOGLE_API_KEY = "AIza...your_key"' > .streamlit/secrets.toml

### Step 4 — Run locally

    streamlit run interface/app.py

---

## Project Structure

    travel_chatbot/
        .streamlit/
            secrets.toml          # GOOGLE_API_KEY (gitignored)
        core/
            chatbot.py            # LangChain agent + system prompt + trip profile
        tools/
            travel_tools.py       # AI-powered tools with rich multi-option data
        interface/
            app.py                # Streamlit UI + auth + rate limiting + PDF export
        config.yaml               # User credentials
        cli.py                    # Command-line interface
        requirements.txt
        README.md

---

## Tool Functions

| Tool                  | What it does                                         |
|-----------------------|------------------------------------------------------|
| search_travel_info    | Live DuckDuckGo search of travel blogs & guides       |
| generate_itinerary    | Rich day-by-day plan with multiple options per slot   |
| estimate_budget       | Cost breakdown with real hotel recommendation         |
| get_destination_tips  | Currency, transport, safety, food, etiquette tips     |
| get_weather_summary   | Temperature, rainfall, packing advice for any month   |

---

## Architecture

    User (browser)
        |
        v
    Streamlit Cloud (app.py)
        |--- Authentication + Rate limiting
        v
    LangChain Agent (Gemini 2.5 Flash via Google AI Studio)
        |--- Calls search_travel_info (DuckDuckGo) 2-3 times
        |    to find current blog/guide recommendations
        |--- Writes the rich response with Maps links,
        |    budget table, must-try foods, hotel suggestions
        v
    Post-processing (chatbot.py)
        |--- Checks all required sections exist; one auto-retry
        |    asks the model to append anything missing
        |--- Rebuilds every Google Maps link from the place name
        v
    User sees a complete travel guide with clickable links

---

## Deploy to Streamlit Community Cloud

1. Push code to GitHub
2. Go to https://share.streamlit.io and sign in
3. New app > select repo > main file: interface/app.py
4. Advanced settings > Secrets: GOOGLE_API_KEY = "AIza..."
5. Deploy and share the URL

