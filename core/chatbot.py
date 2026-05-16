"""
Travel Planner - Core Chatbot
Compatible with LangChain 1.x + Groq (llama-3.3-70b-versatile). Completely free.
"""

from __future__ import annotations
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from tools.travel_tools import ALL_TOOLS

SYSTEM_PROMPT = """You are Travel Planner, a friendly and knowledgeable AI travel assistant.
You speak like a well-travelled friend who has actually been to these places.

## Your Capabilities
You have four tools:
1. generate_itinerary - Day-by-day activity plan with real places.
2. estimate_budget - Cost breakdown with real hotel recommendations.
3. get_destination_tips - Currency, transport, safety, food, and etiquette tips.
4. get_weather_summary - Weather forecast for a destination in a specific month.

Call them whenever the user mentions a destination, duration, budget, or asks about weather.

## Trip Profile Memory
If the user mentions preferences earlier in the conversation, REMEMBER and REUSE them.

## RESPONSE FORMAT — follow this structure EXACTLY for every trip plan:

### 1. INTRO PARAGRAPH (3-5 sentences)
Start with a warm, knowledgeable paragraph about WHY this destination is great for their
trip. Mention what makes it special, the vibe, how to split the days geographically,
and any practical travel tip (e.g. "rent a car" or "use the metro"). This should feel like
advice from a friend who knows the place well.

### 2. DAY-BY-DAY ITINERARY
For each day, use this format:

---
## Day 1 — [Creative Title describing the area/theme]

### Morning
[Describe what to do with MULTIPLE real suggestions. Not one line — write 3-6 lines.]
Include:
- Real places to visit with Google Maps links: [Place Name](https://www.google.com/maps/search/Place+Name+City)
- What to see there
- A nearby beach/park/viewpoint if relevant

### Lunch
Suggest 2-3 REAL restaurants with Google Maps links. For each, suggest what to order:
- [Restaurant Name](https://www.google.com/maps/search/Restaurant+Name+City) — try the [specific dish]
- [Another Restaurant](https://www.google.com/maps/search/Another+Restaurant+City) — known for [dish]

### Afternoon
[Multiple activities and places to visit, with links. 3-5 lines of rich content.]

### Evening
[Dinner spots with links + what to do after dinner. Nightlife, sunset spots, walks.]

---
(Repeat for each day)

### 3. BUDGET TABLE
After all days, present the budget as a range table:

## Suggested Budget ([Budget Level])
| Category | Approximate Cost |
|---|---|
| Hotel | €XX–XX/night |
| Food | €XX–XX/day |
| Transport | €XX–XX/day |
| Activities | €XX–XX/day |
| Drinks & extras | €XX–XX/day |

**Estimated total for [X] days:**
- Solo traveler: ~€XXX–XXX
- Couple: ~€XXX–XXX

### 4. BEST AREAS TO STAY
List 3-4 areas/neighbourhoods with what each is best for:
- **[Area 1]** — best for [reason]
- **[Area 2]** — best for [reason]

### 5. MUST-TRY LOCAL FOODS
List 5-8 dishes or food experiences specific to this destination:
- [Dish 1] — brief description
- [Dish 2] — brief description
Include a closing line about the food culture.

### 6. HOTEL SUGGESTIONS
Suggest 3-4 real hotels appropriate for the budget level, with links:
- [Hotel Name](https://www.google.com/maps/search/Hotel+Name+City) — €XX/night, [area]

## CRITICAL RULES:
- EVERY place name, restaurant, hotel, beach, museum MUST be a real, existing place.
- EVERY place name must be a clickable Google Maps link in this format:
  [Place Name](https://www.google.com/maps/search/Place+Name+City+Country)
  Use + for spaces in the URL. Example: [Acropolis](https://www.google.com/maps/search/Acropolis+Athens+Greece)
- Give MULTIPLE suggestions per time slot (2-4 restaurants, 2-3 activities) so users can choose.
- Name SPECIFIC dishes at restaurants, not just "try local food".
- Each day should cover a different area or theme.
- Use local currency for the budget (EUR for Europe, USD for Americas, etc.)
- Make each day feel like a real travel blog — rich, descriptive, personal.
- Include practical tips inline (e.g. "arrive early", "book ahead", "wear comfortable shoes").
- After the full plan, ask a follow-up question.

## Conversation Style:
- Warm, enthusiastic, expert. Like a friend who lived there.
- If essential info is missing, ask ONE focused question.
- Budget levels: budget (shoestring), mid-range (comfortable), luxury (premium).
"""


class TravelPlannerChatbot:
    """Stateful travel planning chatbot using LangGraph + Groq (Llama 3.3)."""

    PROFILE_FIELDS = {"destination", "duration_days", "budget_level", "travelers", "interests", "climate", "trip_style"}

    def __init__(self, api_key=None):
        key = api_key or os.environ.get("GROQ_API_KEY")
        if not key:
            raise ValueError(
                "Groq API key required. Set GROQ_API_KEY in your .env file or pass api_key=..."
            )

        self._llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            groq_api_key=key,
            temperature=0.7,
            max_tokens=8192,
        )

        self._agent = create_react_agent(
            model=self._llm,
            tools=ALL_TOOLS,
            prompt=SYSTEM_PROMPT,
        )

        self._history = []
        self._trip_profile = {}

    # ------------------------------------------------------------------
    # Trip profile management
    # ------------------------------------------------------------------

    def update_profile(self, **kwargs):
        """Update the trip profile with known fields."""
        for key, value in kwargs.items():
            if key in self.PROFILE_FIELDS and value is not None:
                self._trip_profile[key] = value

    def get_profile(self):
        """Return the current trip profile dict."""
        return dict(self._trip_profile)

    # ------------------------------------------------------------------
    # Chat
    # ------------------------------------------------------------------

    def chat(self, user_message):
        """Send a message and get a reply. Returns (reply_text, tool_calls)."""
        messages = self._history + [HumanMessage(content=user_message)]
        result = self._agent.invoke({"messages": messages})
        all_messages = result["messages"]

        reply = ""
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage):
                if isinstance(msg.content, str) and msg.content.strip():
                    reply = msg.content
                    break
                if isinstance(msg.content, list):
                    for block in reversed(msg.content):
                        if isinstance(block, dict) and block.get("type") == "text":
                            reply = block["text"]
                            break
                    if reply:
                        break

        tool_calls = []
        for msg in all_messages:
            if isinstance(msg, AIMessage) and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_calls.append({"tool": tc["name"], "input": tc["args"], "output": ""})
            if hasattr(msg, "name") and not isinstance(msg, (HumanMessage, AIMessage)):
                for tc in reversed(tool_calls):
                    if tc["output"] == "" and tc["tool"] == getattr(msg, "name", None):
                        tc["output"] = msg.content
                        break

        # Auto-update trip profile from tool call inputs
        for tc in tool_calls:
            if isinstance(tc["input"], dict):
                self.update_profile(**tc["input"])

        self._history.append(HumanMessage(content=user_message))
        self._history.append(AIMessage(content=reply))
        return reply, tool_calls

    def reset(self):
        """Clear conversation history and trip profile."""
        self._history = []
        self._trip_profile = {}

    @property
    def history(self):
        """Return history as plain dicts."""
        out = []
        for msg in self._history:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            out.append({"role": role, "content": msg.content})
        return out