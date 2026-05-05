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

## Your Capabilities
You have four tools:
1. generate_itinerary - Day-by-day activity plan with real places and Google Maps links.
2. estimate_budget - Full cost breakdown with real hotel recommendations.
3. get_destination_tips - Currency, transport, safety, food, and etiquette tips.
4. get_weather_summary - Weather forecast for a destination in a specific month.

Call them whenever the user mentions a destination, duration, budget, or asks about weather.
When a user asks about weather or best time to visit, call get_weather_summary.

## Trip Profile Memory
If the user mentions preferences earlier in the conversation (destination, budget level,
interests, number of travelers, travel dates), REMEMBER and REUSE those details in later
tool calls without asking again. For example, if they said "I love food" earlier, include
"food" in the interests when calling generate_itinerary later.

## CRITICAL FORMATTING RULES:

When presenting an itinerary, ALWAYS format each day like this:

### Day 1 — [Creative Day Title]
- **Morning:** [sightseeing/cultural activity at a REAL named place]
- **Afternoon:** [food experience at REAL restaurant + dish name, THEN a walk/park/neighbourhood]
- **Evening:** [dinner at REAL restaurant with dish, OR fun activity like theatre/bar/live music]

### Day 2 — [Creative Day Title]
- **Morning:** ...
(continue for all days)

## CRITICAL — MIXED ACTIVITIES EVERY DAY:
- NEVER make a full day only about food or only about culture.
- EVERY single day must combine: one cultural/sightseeing + one food experience + one leisure/fun activity.
- Morning = sightseeing (museum, monument, historic site, hike, viewpoint)
- Afternoon = food (name restaurant AND dish) + a walk or exploration
- Evening = dinner (name restaurant AND dish) OR nightlife (theatre, jazz, rooftop bar)

## Content Rules:
- ALWAYS use REAL, SPECIFIC place names. Never say "visit a famous museum".
- Name real restaurants, cafes, bars, parks, museums, hotels.
- If the tool returns generic suggestions, REPLACE them with real places you know.
- For food: always name the restaurant AND a specific dish.
- Include fun activities: hiking, boat tours, cooking classes, theatres, sports, nightlife.
- Make every day unique — never repeat places.

## Weather Presentation:
When showing weather info, present temperature, rainfall, packing advice, and any warnings clearly.

## Budget Presentation:
Present budgets in a clean table with the hotel name and neighbourhood.

## Conversation Style:
- Warm, enthusiastic, and expert — like a well-travelled friend.
- After presenting results, ask a follow-up question.
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