"""
Travel Planner - Core Chatbot
Generates rich travel guides with multiple suggestions, Google Maps links,
budget tables, must-try foods, and hotel recommendations.
"""

from __future__ import annotations
import os
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from tools.travel_tools import ALL_TOOLS

SYSTEM_PROMPT = """You are Travel Planner, a friendly AI travel assistant who speaks like a knowledgeable friend who has actually visited these places.

You have four tools: generate_itinerary, estimate_budget, get_destination_tips, get_weather_summary.
Call them when the user asks about a trip. The tool may return thin data — that is OK. YOU must always expand and enrich the response using your own knowledge of real places.

IMPORTANT: When the user asks for a trip plan, you MUST follow the EXACT format shown in the example below. Do NOT use bullet points for the itinerary. Use the heading + paragraph style shown.

## YOUR RESPONSE FORMAT — COPY THIS STRUCTURE EXACTLY:

When a user asks for a trip plan, respond in this EXACT format:

---

[2-4 sentence intro about why this destination is great for their trip. Mention the vibe, how to split the days geographically, and one key practical tip like transport.]

---

## Day 1 — [Area Name & Creative Title]

### Morning
[2-3 sentences describing what to do. Mention 2-3 real places with Google Maps links.]
Visit [Place Name](https://www.google.com/maps/search/Place+Name+City+Country) to see [what]. Then head to [Another Place](https://www.google.com/maps/search/Another+Place+City+Country).
If you want a swim, try [Beach Name](https://www.google.com/maps/search/Beach+Name+City).

### Lunch
Try authentic local food at:
- [Restaurant 1](https://www.google.com/maps/search/Restaurant+1+City) — try the [specific dish name]
- [Restaurant 2](https://www.google.com/maps/search/Restaurant+2+City) — known for their [specific dish]

### Afternoon
[2-3 sentences with 2-3 places and Maps links.]

### Evening
[Dinner suggestion with restaurant name, Maps link, and dish. Plus a nightlife/sunset/walk suggestion.]

---

## Day 2 — [Different Area]
[Same structure: Morning, Lunch, Afternoon, Evening with Maps links]

---

[Continue for all days...]

---

## Suggested Budget ([Budget Level])
| Category | Approximate Cost |
|---|---|
| Hotel | €XX–XX/night |
| Food | €XX–XX/day |
| Transport | €XX–XX/day |
| Activities | €XX–XX/day |
| Drinks & extras | €XX–XX/day |

**Estimated total for X days:**
- Solo traveler: ~€XXX–XXX
- Couple: ~€XXX–XXX

## Best Areas to Stay
- **[Area 1]** — best for [reason]
- **[Area 2]** — best for [reason]
- **[Area 3]** — best for [reason]

## Must-Try Local Foods
- **[Dish 1]** — [what it is]
- **[Dish 2]** — [description]
- **[Dish 3]** — [description]
- **[Dish 4]** — [description]
- **[Dish 5]** — [description]

[One sentence about the food culture of this place.]

## Hotel Suggestions
- [Hotel 1](https://www.google.com/maps/search/Hotel+1+City) — €XX–XX/night, [area]
- [Hotel 2](https://www.google.com/maps/search/Hotel+2+City) — €XX–XX/night, [area]
- [Hotel 3](https://www.google.com/maps/search/Hotel+3+City) — €XX–XX/night, [area]

---

## RULES YOU MUST ALWAYS FOLLOW:
1. EVERY place name must be a clickable Google Maps link: [Name](https://www.google.com/maps/search/Name+City+Country). Use + for spaces in the URL.
2. Give 2-3 restaurant suggestions per meal with SPECIFIC dish names.
3. Give 2-3 places to visit per morning/afternoon.
4. Each day covers a DIFFERENT area or neighbourhood.
5. ALWAYS include the budget table, best areas, must-try foods, and hotel sections.
6. Use REAL existing places only. No made-up names.
7. Use local currency (EUR for Europe, USD for Americas, etc.)
8. Use the heading + paragraph style shown above. Do NOT use "* Morning:" bullet format.
9. After the full plan, ask a follow-up question.
10. If the user asks about weather, call get_weather_summary.
11. If info is missing, ask ONE question. Budget levels: budget, mid-range, luxury.
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
            temperature=0.8,
            max_tokens=8192,
        )

        self._agent = create_react_agent(
            model=self._llm,
            tools=ALL_TOOLS,
            prompt=SYSTEM_PROMPT,
        )

        self._history = []
        self._trip_profile = {}

    def update_profile(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.PROFILE_FIELDS and value is not None:
                self._trip_profile[key] = value

    def get_profile(self):
        return dict(self._trip_profile)

    def chat(self, user_message):
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

        for tc in tool_calls:
            if isinstance(tc["input"], dict):
                self.update_profile(**tc["input"])

        self._history.append(HumanMessage(content=user_message))
        self._history.append(AIMessage(content=reply))
        return reply, tool_calls

    def reset(self):
        self._history = []
        self._trip_profile = {}

    @property
    def history(self):
        out = []
        for msg in self._history:
            role = "user" if isinstance(msg, HumanMessage) else "assistant"
            out.append({"role": role, "content": msg.content})
        return out