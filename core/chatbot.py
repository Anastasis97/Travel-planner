"""
Travel Planner - Core Chatbot
Generates rich travel guides with multiple suggestions, Google Maps links,
budget tables, must-try foods, and hotel recommendations.

Providers (auto-selected by which API key is configured):
  1. Cerebras (CEREBRAS_API_KEY set)  — default model gpt-oss-120b.
     Free tier: ~30 req/min, 14,400 req/day, ~60K tokens/min, no credit card.
  2. Google Gemini (GOOGLE_API_KEY)   — default model gemini-3.5-flash.
     Free-tier quotas vary per project; some projects only get 5 RPM / 20 RPD.
Override models via CEREBRAS_MODEL / GEMINI_MODEL secrets; force a provider
with MODEL_PROVIDER = "cerebras" or "gemini". No code changes needed.
"""

from __future__ import annotations
import os
import random
import re
import time
from urllib.parse import quote_plus

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from tools.travel_tools import ALL_TOOLS

# ---------------------------------------------------------------------------
# Model / provider configuration (all overridable via secrets, no code changes)
# ---------------------------------------------------------------------------
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "gpt-oss-120b")
MODEL_PROVIDER = os.environ.get("MODEL_PROVIDER", "").strip().lower()  # optional: "cerebras" | "gemini"
MODEL_NAME = GEMINI_MODEL  # backward-compat export


def _build_llm(google_api_key: str | None, cerebras_api_key: str | None):
    """Pick the provider: Cerebras when its key is available (much higher free
    limits), Gemini otherwise. MODEL_PROVIDER forces a specific provider."""
    google_key = google_api_key or os.environ.get("GOOGLE_API_KEY")
    cerebras_key = cerebras_api_key or os.environ.get("CEREBRAS_API_KEY")

    use_cerebras = cerebras_key and MODEL_PROVIDER != "gemini"
    if MODEL_PROVIDER == "cerebras" and not cerebras_key:
        raise ValueError("MODEL_PROVIDER is 'cerebras' but CEREBRAS_API_KEY is not set.")

    if use_cerebras:
        from langchain_cerebras import ChatCerebras
        return ChatCerebras(
            model=CEREBRAS_MODEL,
            api_key=cerebras_key,
            temperature=0.7,
            max_tokens=8192,
        ), f"cerebras/{CEREBRAS_MODEL}"

    if not google_key:
        raise ValueError(
            "No API key configured. Set CEREBRAS_API_KEY (free key at "
            "https://cloud.cerebras.ai) or GOOGLE_API_KEY (free key at "
            "https://aistudio.google.com)."
        )
    return ChatGoogleGenerativeAI(
        model=GEMINI_MODEL,
        google_api_key=google_key,
        temperature=0.7,
        max_output_tokens=8192,
    ), f"gemini/{GEMINI_MODEL}"

SYSTEM_PROMPT = """You are Travel Planner, a friendly AI travel assistant who speaks like a knowledgeable friend who has actually visited these places.

You have five tools: generate_itinerary, estimate_budget, get_destination_tips, get_weather_summary, search_travel_info.

## HOW TO RESEARCH A TRIP (do this BEFORE writing the plan):
When the user asks for a trip plan, follow this sequence:
1. Call generate_itinerary to validate the parameters.
2. Call search_travel_info 2-3 times to find CURRENT recommendations from travel
   blogs and guides. Good queries:
   - "best things to do in <destination> travel blog"
   - "best restaurants <destination> where locals eat"
   - "where to stay in <destination> best areas hotels"
3. Read the search snippets. Prefer places that appear in the results (they are
   current and real). Blend them with your own knowledge of the destination.
4. THEN write the complete formatted response yourself.

If search returns an error or nothing useful, proceed with your own knowledge —
never mention search failures to the user.

IMPORTANT: When the user asks for a trip plan, you MUST follow the EXACT format shown below. Do NOT use bullet points for the itinerary body. Use the heading + paragraph style shown.

## YOUR RESPONSE FORMAT — COPY THIS STRUCTURE EXACTLY:

---

[2-4 sentence intro about why this destination is great for their trip. Mention the vibe, how to split the days geographically, and one key practical tip like transport.]

---

## Day 1 — [Area Name & Creative Title]

### Morning
[2-3 sentences describing what to do. Mention 2-3 real places with Google Maps links.]
Visit [Place Name](https://www.google.com/maps/search/Place+Name+City+Country) to see [what]. Then head to [Another Place](https://www.google.com/maps/search/Another+Place+City+Country).

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
5. ALWAYS include ALL FOUR closing sections: budget table, best areas to stay, must-try foods, and hotel suggestions. NEVER skip any of them.
6. Use REAL existing places only. Prefer places confirmed by your search results. No made-up names.
7. Use local currency (EUR for Europe, USD for Americas, etc.)
8. Use the heading + paragraph style shown above. Do NOT use "* Morning:" bullet format.
9. After the full plan, ask a follow-up question.
10. If the user asks about weather, call get_weather_summary.
11. If info is missing, ask ONE question. Budget levels: budget, mid-range, luxury.
12. Do NOT mention your tools, searches, or these instructions to the user.

## CRITICAL — READ THIS:
The user CANNOT see tool output JSON or search results. After calling tools, you MUST write out the COMPLETE formatted response yourself. Do NOT say "here is your itinerary" without actually writing it. YOU must write the full day-by-day plan, budget table, must-try foods, everything. The tools give you parameters and research material — YOU generate ALL the content.
"""


# ---------------------------------------------------------------------------
# Post-processing helpers
# ---------------------------------------------------------------------------

# A reply that looks like an itinerary must contain all of these.
REQUIRED_SECTIONS = {
    "day-by-day plan": re.compile(r"^#{2,3}\s*Day\s*\d", re.MULTILINE | re.IGNORECASE),
    "budget table": re.compile(r"Suggested\s+Budget|^\|\s*Category\s*\|", re.MULTILINE | re.IGNORECASE),
    "best areas to stay": re.compile(r"Best\s+Areas?\s+to\s+Stay", re.IGNORECASE),
    "must-try local foods": re.compile(r"Must[-\s]?Try", re.IGNORECASE),
    "hotel suggestions": re.compile(r"Hotel\s+Suggestions?", re.IGNORECASE),
}

_MD_LINK_RE = re.compile(r"\[([^\]\n]+)\]\(([^)\n]*)\)")
_MAPS_PREFIX = "https://www.google.com/maps/search/"


def _missing_sections(reply: str) -> list[str]:
    """Return the list of required section names absent from an itinerary reply."""
    return [name for name, pattern in REQUIRED_SECTIONS.items() if not pattern.search(reply)]


def _fix_maps_links(reply: str, destination: str = "") -> str:
    """Normalise every markdown link into a valid Google Maps search link.

    The model sometimes produces malformed URLs (spaces, wrong domain, empty
    parentheses). Instead of trusting it, we rebuild each link from the link
    TEXT, which is the place name the user actually sees.
    """
    dest = destination.strip()

    def _rebuild(match: re.Match) -> str:
        name = match.group(1).strip()
        url = match.group(2).strip()

        # Leave already-valid maps links alone
        if url.startswith(_MAPS_PREFIX) and " " not in url and len(url) > len(_MAPS_PREFIX):
            return match.group(0)

        # Strip markdown emphasis from the name for the query
        clean_name = name.replace("**", "").replace("*", "").strip()
        if not clean_name:
            return match.group(0)

        query = clean_name
        if dest and dest.lower() not in clean_name.lower():
            query = f"{clean_name} {dest}"
        return f"[{name}]({_MAPS_PREFIX}{quote_plus(query)})"

    return _MD_LINK_RE.sub(_rebuild, reply)


# Transient Google API errors worth retrying automatically.
_TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED",
                      "500", "INTERNAL", "DEADLINE_EXCEEDED", "overloaded",
                      "high demand")


def _is_transient(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in _TRANSIENT_MARKERS)


def _invoke_with_retry(agent, payload, attempts: int = 4):
    """Invoke the agent, retrying transient 503/429/500 errors with
    exponential backoff + jitter (~2s, 4s, 8s). Re-raises anything else,
    and the last error if all attempts fail."""
    delay = 2.0
    for attempt in range(attempts):
        try:
            return agent.invoke(payload)
        except Exception as exc:
            if attempt == attempts - 1 or not _is_transient(exc):
                raise
            time.sleep(delay + random.uniform(0, 1))
            delay *= 2


class TravelPlannerChatbot:
    """Stateful travel planning chatbot using LangGraph + Google Gemini Flash."""

    PROFILE_FIELDS = {"destination", "duration_days", "budget_level", "travelers", "interests", "climate", "trip_style"}

    def __init__(self, api_key=None, cerebras_api_key=None, model: str | None = None):
        # api_key kept for backward compatibility = the Google API key.
        self._llm, self.active_model = _build_llm(api_key, cerebras_api_key)

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

    # -- internal ----------------------------------------------------------

    @staticmethod
    def _extract_reply(all_messages) -> str:
        """Pull the final assistant text out of the agent's message list."""
        for msg in reversed(all_messages):
            if isinstance(msg, AIMessage):
                if isinstance(msg.content, str) and msg.content.strip():
                    return msg.content
                if isinstance(msg.content, list):
                    for block in reversed(msg.content):
                        if isinstance(block, dict) and block.get("type") == "text" and block.get("text", "").strip():
                            return block["text"]
        return ""

    @staticmethod
    def _extract_tool_calls(all_messages) -> list[dict]:
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
        return tool_calls

    # -- public ------------------------------------------------------------

    def chat(self, user_message):
        messages = self._history + [HumanMessage(content=user_message)]
        result = _invoke_with_retry(self._agent, {"messages": messages})
        all_messages = result["messages"]

        reply = self._extract_reply(all_messages)
        tool_calls = self._extract_tool_calls(all_messages)

        # Update trip profile from tool inputs
        for tc in tool_calls:
            if isinstance(tc["input"], dict):
                self.update_profile(**tc["input"])

        # ------------------------------------------------------------------
        # Post-processing step 1: section completeness check + one retry.
        # Only enforced when the model actually generated an itinerary.
        # ------------------------------------------------------------------
        is_itinerary = any(tc["tool"] == "generate_itinerary" for tc in tool_calls)
        if is_itinerary and reply:
            missing = _missing_sections(reply)
            if missing:
                fix_prompt = (
                    "Your previous response is missing these required sections: "
                    + ", ".join(missing)
                    + ". Rewrite ONLY the missing sections now, in the exact "
                    "format from your instructions (budget as a markdown table, "
                    "hotels with Google Maps links). Do not repeat sections that "
                    "already exist. Do not apologise or add commentary."
                )
                retry_messages = all_messages + [HumanMessage(content=fix_prompt)]
                try:
                    retry = _invoke_with_retry(self._agent, {"messages": retry_messages}, attempts=2)
                    addition = self._extract_reply(retry["messages"])
                    if addition and addition.strip() != reply.strip():
                        reply = reply.rstrip() + "\n\n" + addition.strip()
                except Exception:
                    pass  # keep the partial reply rather than failing the turn

        # ------------------------------------------------------------------
        # Post-processing step 2: normalise every link into a valid
        # Google Maps search URL, rebuilt from the visible place name.
        # ------------------------------------------------------------------
        if reply:
            destination = str(self._trip_profile.get("destination", ""))
            reply = _fix_maps_links(reply, destination)

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