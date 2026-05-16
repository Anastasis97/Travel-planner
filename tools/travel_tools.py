"""
Travel Planner Tool Functions
Uses Groq LLM to generate real, location-specific recommendations for ANY city.
Falls back gracefully if the API call fails.
"""

import json
import os
import random
from urllib.parse import quote_plus
from langchain_core.tools import tool

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass



# ---------------------------------------------------------------------------
# Google Maps link helper
# ---------------------------------------------------------------------------

def make_google_maps_link(query: str) -> str:
    """Generate a Google Maps search URL from a place name or address."""
    return f"https://www.google.com/maps/search/{quote_plus(query)}"


def _extract_place_name(activity_text: str) -> str:
    """Extract the short place/restaurant name from an activity description.

    Examples:
        'Visit the Colosseum, one of Rome\\'s most iconic landmarks' -> 'Colosseum'
        'Lunch at Diporto Agoras - try the lamb stew' -> 'Diporto Agoras'
        'Explore the Trastevere neighbourhood' -> 'Trastevere'
    """
    import re
    text = activity_text.strip()

    # Pattern 1: "... at [PLACE NAME] -/,/—" (restaurants, venues)
    match = re.search(r'\bat\s+(?:the\s+)?(.+?)(?:\s*[-,—]|\s*$)', text)
    if match:
        name = match.group(1).strip().rstrip('.')
        # Take up to 5 words max
        words = name.split()
        if len(words) <= 5:
            return name

    # Pattern 2: "Visit/Explore/Tour the [PLACE NAME] -/,/—"
    match = re.search(r'(?:Visit|Explore|Tour|See|Walk|Wander)\s+(?:the\s+)?(.+?)(?:\s*[-,—]|\s+and\s|\s+then\s|\s*$)', text, re.IGNORECASE)
    if match:
        name = match.group(1).strip().rstrip('.')
        words = name.split()
        if len(words) <= 5:
            return name

    # Fallback: take first 4 meaningful words after removing leading verbs
    text = re.sub(r'^(Visit|Explore|Tour|Enjoy|Take|Try|See|Walk|Wander|Grab|Have|Dine|Lunch|Breakfast|Dinner)\s+(a\s+|the\s+|an\s+)?', '', text, flags=re.IGNORECASE)
    words = text.split()
    short = ' '.join(words[:4]).rstrip('.,;:-')
    return short

# ---------------------------------------------------------------------------
# LLM-powered recommendation engine (uses langchain_groq — already installed)
# ---------------------------------------------------------------------------

def _ask_llm(prompt: str) -> str | None:
    """Call Groq via langchain_groq to generate location-specific data.
    Tries st.secrets first (Streamlit Cloud), then env var (local dev)."""
    try:
        from langchain_groq import ChatGroq
        from langchain_core.messages import HumanMessage, SystemMessage

        # Try Streamlit secrets first, then env var
        api_key = ""
        try:
            import streamlit as st
            api_key = st.secrets.get("GROQ_API_KEY", "")
        except Exception:
            pass
        if not api_key:
            api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return None

        llm = ChatGroq(
            model="llama-3.1-8b-instant",
            groq_api_key=api_key,
            temperature=0.9,
            max_tokens=3000,
        )

        messages = [
            SystemMessage(content="You are a travel data API. Return ONLY valid JSON. No markdown, no backticks, no explanation, no preamble. Just the JSON object."),
            HumanMessage(content=prompt),
        ]

        response = llm.invoke(messages)
        text = response.content.strip()

        # Strip markdown fences if the model adds them anyway
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            if "```" in text:
                text = text[:text.rfind("```")].strip()
        return text
    except Exception as e:
        print(f"[Tool LLM] Error: {e}")
        return None


def _generate_itinerary_via_llm(destination, duration_days, budget_level, interests):
    """Ask LLM to generate a rich itinerary with multiple suggestions per slot."""
    interests_str = ", ".join(interests)
    prompt = f"""Create a detailed {duration_days}-day travel itinerary for {destination}, {budget_level} budget.
Traveler interests: {interests_str}.

Return ONLY this JSON structure:
{{
  "intro": "3-5 sentence paragraph about why {destination} is great for this trip, the vibe, how to split the days geographically, and a key practical tip (transport, best areas, etc.)",
  "days": [
    {{
      "day": 1,
      "theme": "Area Name & Creative Title",
      "morning": {{
        "description": "What to do and see in the morning (2-3 sentences)",
        "places": ["Real Place 1", "Real Place 2", "Real Place 3"],
        "tip": "One practical tip like 'arrive early' or 'wear comfortable shoes'"
      }},
      "lunch": {{
        "restaurants": [
          {{"name": "Real Restaurant Name", "dish": "specific dish to order"}},
          {{"name": "Another Restaurant", "dish": "their signature dish"}}
        ]
      }},
      "afternoon": {{
        "description": "What to do in the afternoon (2-3 sentences)",
        "places": ["Real Place 1", "Real Place 2"]
      }},
      "evening": {{
        "description": "Dinner and nightlife suggestions",
        "restaurants": [
          {{"name": "Dinner Restaurant", "dish": "what to order"}}
        ],
        "activities": ["Bar/nightlife/sunset spot suggestion"]
      }}
    }}
  ],
  "hotels": [
    {{"name": "Real Hotel Name", "price_range": "€XX-XX/night", "area": "neighbourhood name"}},
    {{"name": "Another Hotel", "price_range": "€XX-XX/night", "area": "area"}},
    {{"name": "Third Option", "price_range": "€XX-XX/night", "area": "area"}}
  ],
  "budget": {{
    "currency": "EUR",
    "hotel_range": "€XX-XX/night",
    "food_range": "€XX-XX/day",
    "transport_range": "€XX-XX/day",
    "activities_range": "€XX-XX/day",
    "drinks_extras_range": "€XX-XX/day",
    "total_solo": "€XXX-XXX",
    "total_couple": "€XXX-XXX"
  }},
  "best_areas": [
    {{"name": "Area Name", "best_for": "reason"}},
    {{"name": "Area 2", "best_for": "reason"}}
  ],
  "must_try_foods": [
    {{"name": "Dish Name", "description": "brief description"}},
    {{"name": "Another Dish", "description": "what it is"}},
    {{"name": "Third Dish", "description": "why try it"}},
    {{"name": "Fourth Dish", "description": "what makes it special"}},
    {{"name": "Fifth Dish", "description": "local favourite"}}
  ],
  "food_culture_note": "One sentence about the destination's food culture."
}}

RULES:
- Every place, restaurant, hotel MUST be real and existing in {destination}.
- Name SPECIFIC dishes (e.g. "sardines from Kalloni" not "local fish").
- Give 2-3 restaurant options per meal so users can choose.
- Give 2-3 places to visit per time slot.
- Each day should cover a DIFFERENT area or neighbourhood.
- Include beaches, viewpoints, markets, museums, walks — variety is key.
- Prices should be realistic for {destination} at {budget_level} level.
- Use local currency."""

    text = _ask_llm(prompt)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _generate_budget_via_llm(destination, duration_days, budget_level, travelers):
    """Ask LLM for real hotel recommendation and price estimates."""
    prompt = f"""Estimate travel budget for {travelers} person(s), {duration_days} days in {destination}, {budget_level} budget.

Return ONLY this JSON:
{{"recommended_hotel": {{
    "name": "[REAL existing hotel/hostel name in {destination}]",
    "rating": 4.3,
    "price_per_night": 120,
    "area": "[real neighbourhood]"
  }},
  "transport_mode": "[best transport for {budget_level} in {destination}]",
  "daily_costs": {{"food": 50, "activities": 30, "local_transport": 15}},
  "currency": "EUR",
  "tips": "[one money-saving tip specific to {destination}]"
}}

RULES:
- Hotel MUST be real and existing.
- Prices in USD, realistic for {destination} at {budget_level} level.
- budget=hostels/street food, mid-range=3-4 star/good restaurants, luxury=5-star/fine dining."""

    text = _ask_llm(prompt)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _generate_tips_via_llm(destination):
    """Ask LLM for destination-specific travel tips."""
    prompt = f"""Give practical travel tips for {destination}.

Return ONLY this JSON:
{{"currency": "[currency name/code, ATM info, card acceptance]",
  "language": "[languages spoken, English level, 3 useful phrases with translations]",
  "transport": "[how to get around, specific apps/cards to use]",
  "best_time_to_visit": "[best months and why, months to avoid]",
  "safety": "[specific safety tips for {destination}]",
  "food_tip": "[what to eat, where locals eat, dishes to try by name]",
  "etiquette": "[cultural norms, dress codes, tipping customs]"
}}

Every tip must be SPECIFIC to {destination} with real names."""

    text = _ask_llm(prompt)
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Fallback data
# ---------------------------------------------------------------------------

TRANSPORT_MODES = {
    "budget": {"mode": "public transit + walking", "daily_cost": 5},
    "mid-range": {"mode": "mix of taxis, metro, and rideshare", "daily_cost": 20},
    "luxury": {"mode": "private transfers and car hire", "daily_cost": 80},
}


# ---------------------------------------------------------------------------
# Tool 1 - generate_itinerary
# ---------------------------------------------------------------------------

@tool
def generate_itinerary(
    destination: str,
    duration_days: int,
    budget_level: str,
    interests: list[str] | None = None,
) -> str:
    """
    Validate trip parameters and trigger the assistant to generate a rich itinerary.
    The assistant will use its own knowledge to create a detailed plan with real places.

    Args:
        destination: City to visit (e.g. "Athens", "Tokyo", "Lisbon", "Seoul").
        duration_days: Number of days for the trip (1-30).
        budget_level: One of 'budget', 'mid-range', or 'luxury'.
        interests: Optional list from: 'cultural', 'outdoor', 'food', 'relaxation'.

    Returns:
        A JSON string with validated parameters. The assistant must generate the full
        rich itinerary with real places, Maps links, budget, must-try foods, and hotels.
    """
    duration_days = max(1, min(30, duration_days))
    budget_level = budget_level.lower().strip()
    if budget_level not in ("budget", "mid-range", "luxury"):
        budget_level = "mid-range"
    if not interests:
        interests = ["cultural", "food"]
    interests = [i for i in interests if i in ("cultural", "outdoor", "food", "relaxation")]
    if not interests:
        interests = ["cultural", "food"]

    result = {
        "destination": destination,
        "duration_days": duration_days,
        "budget_level": budget_level,
        "interests": interests,
        "instruction": (
            f"Generate a COMPLETE rich travel guide for {duration_days} days in {destination} "
            f"on a {budget_level} budget. You MUST include ALL of the following sections "
            f"using REAL places you know in {destination}: "
            f"1) Intro paragraph about the destination, "
            f"2) Day-by-day itinerary with Morning/Lunch/Afternoon/Evening headings, "
            f"multiple place suggestions per slot with Google Maps links, "
            f"3) Budget table with cost ranges, "
            f"4) Best areas to stay, "
            f"5) Must-try local foods, "
            f"6) Hotel suggestions with Maps links. "
            f"Follow the EXACT format from your system instructions."
        ),
    }

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 2 - estimate_budget
# ---------------------------------------------------------------------------

@tool
def estimate_budget(
    destination: str,
    duration_days: int,
    budget_level: str,
    travelers: int = 1,
) -> str:
    """
    Estimate total trip budget with a real hotel recommendation for ANY destination.

    Args:
        destination: The travel destination.
        duration_days: Number of travel days.
        budget_level: One of 'budget', 'mid-range', or 'luxury'.
        travelers: Number of people travelling (default 1).

    Returns:
        A JSON string with hotel recommendation, cost breakdown, and total.
    """
    duration_days = max(1, min(30, duration_days))
    travelers = max(1, min(20, travelers))
    budget_level = budget_level.lower().strip()
    if budget_level not in ("budget", "mid-range", "luxury"):
        budget_level = "mid-range"

    transport_info = TRANSPORT_MODES[budget_level]

    # Use realistic defaults per budget level — the main agent will enrich with real hotel names
    defaults = {
        "budget":    {"price": 30, "food": 25, "activities": 12},
        "mid-range": {"price": 110, "food": 55, "activities": 35},
        "luxury":    {"price": 380, "food": 160, "activities": 90},
    }
    d = defaults[budget_level]

    rooms = max(1, (travelers + 1) // 2)
    accommodation = d["price"] * duration_days * rooms
    transport_local = transport_info["daily_cost"] * duration_days * travelers
    food = d["food"] * duration_days * travelers
    activities = d["activities"] * duration_days * travelers
    misc = round((accommodation + transport_local + food + activities) * 0.08)
    total = accommodation + transport_local + food + activities + misc

    result = {
        "destination": destination,
        "duration_days": duration_days,
        "travelers": travelers,
        "budget_level": budget_level,
        "transport_mode": transport_info["mode"],
        "cost_breakdown": {
            "accommodation": accommodation,
            "local_transport": transport_local,
            "food_and_dining": food,
            "activities": activities,
            "miscellaneous": misc,
        },
        "total_estimated": total,
        "per_person": round(total / travelers),
        "instruction": (
            f"Present this budget for {destination} using LOCAL CURRENCY. "
            f"Suggest 3 REAL hotels with Google Maps links appropriate for {budget_level} budget. "
            f"Present as a clean table with cost ranges, not exact numbers."
        ),
    }
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 3 - get_packing_list
# ---------------------------------------------------------------------------

@tool
def get_packing_list(
    destination: str,
    duration_days: int,
    climate: str = "temperate",
    trip_style: str = "mixed",
) -> str:
    """
    Generate a personalised packing list for any destination.

    Args:
        destination: Travel destination.
        duration_days: Length of stay in days.
        climate: 'tropical', 'cold', 'desert', 'mediterranean', or 'temperate'.
        trip_style: 'backpacking', 'business', 'beach', or 'mixed'.

    Returns:
        A JSON string with categorised packing recommendations.
    """
    climate_map = {
        "tropical": ["Lightweight shorts", "Rain jacket", "Sandals", "Sun hat", "Swimwear", "Insect repellent"],
        "cold": ["Thermal layers", "Warm jacket", "Gloves and scarf", "Waterproof boots", "Beanie"],
        "desert": ["Light long-sleeve shirts", "Wide-brim hat", "Linen trousers", "High-SPF sunscreen"],
        "mediterranean": ["Light layers", "Sunscreen SPF 50+", "Sandals", "Light evening jacket", "Swimwear"],
        "temperate": ["Jeans or chinos", "Light jacket", "Layers for variable weather", "Waterproof layer"],
    }
    style_map = {
        "backpacking": ["35-50L backpack", "Padlock", "Quick-dry towel", "Water bottle", "Portable charger"],
        "business": ["2x business outfits", "Laptop and charger", "Portable steamer", "Professional shoes"],
        "beach": ["Multiple swimsuits", "Beach towel", "Snorkelling gear", "Waterproof phone pouch"],
        "mixed": ["Smart-casual outfits", "Foldable tote bag", "One smart dinner outfit"],
    }
    essentials = [
        "Passport and documents (plus digital copies)",
        "Travel insurance documents",
        "Local currency + backup card",
        "Phone charger and travel adapter",
        "First-aid kit and prescriptions",
        "Sunscreen SPF 50+",
    ]
    toiletries = ["Toothbrush and toothpaste", "Shampoo/conditioner", "Deodorant", "Face wash", "Lip balm"]

    result = {
        "destination": destination,
        "duration_days": duration_days,
        "climate": climate,
        "trip_style": trip_style,
        "packing_list": {
            "essentials": essentials,
            "clothing_base": ["T-shirts (1 per day, max 5)", "Comfortable walking shoes", "Underwear and socks"],
            f"clothing_{climate}": climate_map.get(climate, climate_map["temperate"]),
            f"{trip_style}_gear": style_map.get(trip_style, style_map["mixed"]),
            "toiletries": toiletries,
        },
        "tip": "Pack one fewer outfit than you think!" if duration_days > 5 else "Travel light!",
    }
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 4 - get_destination_tips
# ---------------------------------------------------------------------------

@tool
def get_destination_tips(destination: str) -> str:
    """
    Trigger the assistant to provide real, specific travel tips for a destination.

    Args:
        destination: The travel destination.

    Returns:
        A JSON string. The assistant must generate specific tips using its own knowledge.
    """
    result = {
        "destination": destination,
        "instruction": (
            f"Provide SPECIFIC travel tips for {destination} covering: "
            f"currency (name, ATMs, cards), language (what's spoken, 3 useful phrases), "
            f"transport (how to get around, apps to use), best time to visit, "
            f"safety tips, food recommendations (specific dishes and restaurants), "
            f"and local etiquette. Use YOUR knowledge — be specific, not generic."
        ),
        "general_tips": [
            "Keep digital copies of your passport.",
            "Get travel insurance before departure.",
            "Tell your bank about your travel dates.",
            "Download offline maps before you go.",
        ],
    }
    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Tool 4 - get_weather_summary
# ---------------------------------------------------------------------------

# Climate data for common destination regions
_CLIMATE_DATA = {
    "tropical": {
        "jan": {"temp": "24-32°C", "rain": "high", "warning": "Monsoon season in some regions."},
        "feb": {"temp": "24-32°C", "rain": "high", "warning": "Heavy rainfall possible."},
        "mar": {"temp": "25-33°C", "rain": "moderate", "warning": "Humidity increasing."},
        "apr": {"temp": "26-34°C", "rain": "moderate", "warning": "Hot and humid."},
        "may": {"temp": "26-34°C", "rain": "moderate", "warning": "Pre-monsoon heat."},
        "jun": {"temp": "25-32°C", "rain": "high", "warning": "Monsoon season beginning."},
        "jul": {"temp": "24-31°C", "rain": "very high", "warning": "Peak monsoon — expect heavy rain."},
        "aug": {"temp": "24-31°C", "rain": "very high", "warning": "Peak monsoon continues."},
        "sep": {"temp": "24-31°C", "rain": "high", "warning": "Monsoon tapering off."},
        "oct": {"temp": "25-32°C", "rain": "moderate", "warning": "Occasional storms."},
        "nov": {"temp": "24-31°C", "rain": "moderate", "warning": "Pleasant but humid."},
        "dec": {"temp": "24-30°C", "rain": "low", "warning": "Dry season — great time to visit."},
    },
    "mediterranean": {
        "jan": {"temp": "5-13°C", "rain": "moderate", "warning": "Cool and rainy — pack layers."},
        "feb": {"temp": "6-14°C", "rain": "moderate", "warning": "Still cool, improving."},
        "mar": {"temp": "8-16°C", "rain": "moderate", "warning": "Spring beginning — pleasant."},
        "apr": {"temp": "11-20°C", "rain": "low", "warning": "Excellent travel weather."},
        "may": {"temp": "15-25°C", "rain": "low", "warning": "Ideal month — warm, not crowded."},
        "jun": {"temp": "20-30°C", "rain": "very low", "warning": "Hot — stay hydrated."},
        "jul": {"temp": "23-33°C", "rain": "very low", "warning": "Peak heat — avoid midday sun."},
        "aug": {"temp": "23-33°C", "rain": "very low", "warning": "Very hot and crowded."},
        "sep": {"temp": "19-28°C", "rain": "low", "warning": "Great shoulder season."},
        "oct": {"temp": "15-23°C", "rain": "moderate", "warning": "Cooling down — still pleasant."},
        "nov": {"temp": "10-17°C", "rain": "moderate", "warning": "Rain returning."},
        "dec": {"temp": "6-14°C", "rain": "moderate", "warning": "Cool — pack warm layers."},
    },
    "temperate": {
        "jan": {"temp": "-2-5°C", "rain": "moderate", "warning": "Cold — pack winter clothes."},
        "feb": {"temp": "-1-6°C", "rain": "moderate", "warning": "Still cold, days lengthening."},
        "mar": {"temp": "3-11°C", "rain": "moderate", "warning": "Early spring — variable weather."},
        "apr": {"temp": "7-15°C", "rain": "moderate", "warning": "Mild — bring a rain jacket."},
        "may": {"temp": "11-19°C", "rain": "moderate", "warning": "Pleasant — great for walking."},
        "jun": {"temp": "15-23°C", "rain": "low", "warning": "Warm and sunny — peak season starting."},
        "jul": {"temp": "17-26°C", "rain": "low", "warning": "Warmest month — popular tourist time."},
        "aug": {"temp": "17-25°C", "rain": "low", "warning": "Warm — can be crowded."},
        "sep": {"temp": "13-21°C", "rain": "moderate", "warning": "Autumn starting — lovely colours."},
        "oct": {"temp": "9-15°C", "rain": "moderate", "warning": "Cool — layer up."},
        "nov": {"temp": "4-9°C", "rain": "moderate", "warning": "Getting cold — shorter days."},
        "dec": {"temp": "0-5°C", "rain": "moderate", "warning": "Winter — Christmas markets!"},
    },
    "cold": {
        "jan": {"temp": "-15-(-5)°C", "rain": "low (snow)", "warning": "Extreme cold — dress in layers."},
        "feb": {"temp": "-14-(-4)°C", "rain": "low (snow)", "warning": "Still very cold."},
        "mar": {"temp": "-8-2°C", "rain": "low", "warning": "Warming slowly."},
        "apr": {"temp": "-2-8°C", "rain": "moderate", "warning": "Spring thaw beginning."},
        "may": {"temp": "5-15°C", "rain": "moderate", "warning": "Pleasant but cool evenings."},
        "jun": {"temp": "10-20°C", "rain": "moderate", "warning": "Best summer month."},
        "jul": {"temp": "13-23°C", "rain": "moderate", "warning": "Warmest — midnight sun possible."},
        "aug": {"temp": "11-20°C", "rain": "moderate", "warning": "Still pleasant."},
        "sep": {"temp": "6-14°C", "rain": "moderate", "warning": "Autumn arriving fast."},
        "oct": {"temp": "0-7°C", "rain": "moderate", "warning": "Cold returning — Northern Lights season."},
        "nov": {"temp": "-7-0°C", "rain": "low (snow)", "warning": "Winter setting in."},
        "dec": {"temp": "-12-(-3)°C", "rain": "low (snow)", "warning": "Deep winter — very short days."},
    },
    "desert": {
        "jan": {"temp": "10-22°C", "rain": "very low", "warning": "Cool and pleasant."},
        "feb": {"temp": "12-25°C", "rain": "very low", "warning": "Warming up."},
        "mar": {"temp": "16-29°C", "rain": "very low", "warning": "Ideal travel weather."},
        "apr": {"temp": "21-35°C", "rain": "very low", "warning": "Getting hot."},
        "may": {"temp": "26-40°C", "rain": "very low", "warning": "Very hot — limit midday exposure."},
        "jun": {"temp": "29-43°C", "rain": "none", "warning": "Extreme heat — dangerous midday."},
        "jul": {"temp": "30-45°C", "rain": "none", "warning": "Peak heat — avoid if possible."},
        "aug": {"temp": "30-44°C", "rain": "none", "warning": "Extreme heat continues."},
        "sep": {"temp": "27-40°C", "rain": "very low", "warning": "Still very hot."},
        "oct": {"temp": "22-34°C", "rain": "very low", "warning": "Cooling — pleasant evenings."},
        "nov": {"temp": "15-27°C", "rain": "very low", "warning": "Great travel weather."},
        "dec": {"temp": "11-22°C", "rain": "very low", "warning": "Cool and comfortable."},
    },
}

# Map common destinations to climate zones
_DESTINATION_CLIMATES = {
    "athens": "mediterranean", "rome": "mediterranean", "barcelona": "mediterranean",
    "lisbon": "mediterranean", "istanbul": "mediterranean", "dubrovnik": "mediterranean",
    "naples": "mediterranean", "marseille": "mediterranean", "nice": "mediterranean",
    "tokyo": "temperate", "london": "temperate", "paris": "temperate",
    "new york": "temperate", "berlin": "temperate", "amsterdam": "temperate",
    "prague": "temperate", "vienna": "temperate", "munich": "temperate",
    "seoul": "temperate", "toronto": "temperate", "chicago": "temperate",
    "sydney": "temperate", "melbourne": "temperate", "buenos aires": "temperate",
    "bangkok": "tropical", "bali": "tropical", "singapore": "tropical",
    "mumbai": "tropical", "hanoi": "tropical", "ho chi minh": "tropical",
    "cartagena": "tropical", "cancun": "tropical", "phuket": "tropical",
    "reykjavik": "cold", "oslo": "cold", "helsinki": "cold",
    "stockholm": "cold", "copenhagen": "cold", "edinburgh": "cold",
    "dubai": "desert", "marrakech": "desert", "cairo": "desert",
    "doha": "desert", "riyadh": "desert", "phoenix": "desert",
}

_MONTH_MAP = {
    "january": "jan", "february": "feb", "march": "mar", "april": "apr",
    "may": "may", "june": "jun", "july": "jul", "august": "aug",
    "september": "sep", "october": "oct", "november": "nov", "december": "dec",
    "jan": "jan", "feb": "feb", "mar": "mar", "apr": "apr",
    "jun": "jun", "jul": "jul", "aug": "aug", "sep": "sep",
    "oct": "oct", "nov": "nov", "dec": "dec",
}

_PACKING_ADVICE = {
    "tropical": "Lightweight breathable clothing, rain jacket, sandals, insect repellent, high-SPF sunscreen.",
    "mediterranean": "Light layers, sunscreen, comfortable walking shoes, sunglasses, a hat for midday sun.",
    "temperate": "Layers for variable weather, waterproof jacket, comfortable shoes, umbrella.",
    "cold": "Thermal underlayers, insulated jacket, waterproof boots, gloves, scarf, beanie.",
    "desert": "Light long-sleeve shirts, wide-brim hat, high-SPF sunscreen, plenty of water, sunglasses.",
}


@tool
def get_weather_summary(
    destination: str,
    month: str | None = None,
) -> str:
    """
    Get expected weather conditions for a destination in a given month.
    Useful for packing advice and choosing the best time to visit.

    Args:
        destination: City name (e.g. "Athens", "Tokyo", "Bangkok").
        month: Month name (e.g. "march", "july"). Defaults to general overview if not provided.

    Returns:
        A JSON string with temperature range, rainfall, packing advice, and travel warnings.
    """
    dest_key = destination.lower().strip().rstrip(".")
    # Try to find climate zone
    climate_zone = _DESTINATION_CLIMATES.get(dest_key, "temperate")

    month_key = None
    if month:
        month_key = _MONTH_MAP.get(month.lower().strip())

    climate = _CLIMATE_DATA.get(climate_zone, _CLIMATE_DATA["temperate"])

    if month_key and month_key in climate:
        data = climate[month_key]
        result = {
            "destination": destination,
            "month": month,
            "climate_zone": climate_zone,
            "expected_temperature_range": data["temp"],
            "rainfall_level": data["rain"],
            "packing_advice": _PACKING_ADVICE.get(climate_zone, _PACKING_ADVICE["temperate"]),
            "travel_warning": data["warning"],
        }
    else:
        # General overview — pick the best and worst months
        best = min(climate.items(), key=lambda x: ("low" in x[1]["rain"].lower()) * -1)
        worst = max(climate.items(), key=lambda x: ("high" in x[1]["rain"].lower()) * 1)
        result = {
            "destination": destination,
            "month": "general overview",
            "climate_zone": climate_zone,
            "expected_temperature_range": f"Varies by season — e.g. {climate['jan']['temp']} in winter, {climate['jul']['temp']} in summer",
            "rainfall_level": f"Varies — lowest around {best[0].capitalize()}, highest around {worst[0].capitalize()}",
            "packing_advice": _PACKING_ADVICE.get(climate_zone, _PACKING_ADVICE["temperate"]),
            "travel_warning": "Check the specific month you plan to travel for accurate weather.",
        }

    return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Public registry
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    generate_itinerary,
    estimate_budget,
    get_destination_tips,
    get_weather_summary,
]