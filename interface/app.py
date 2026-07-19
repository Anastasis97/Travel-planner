"""
Travel Planner – Streamlit Web Interface
Run:  streamlit run interface/app.py
"""

from __future__ import annotations

import json
import os
import sys
import io
import re
import sqlite3
from datetime import date

# Make sure the project root is on sys.path when run from the interface/ directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import yaml
import streamlit as st
import streamlit_authenticator as stauth
from core.chatbot import TravelPlannerChatbot


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DAILY_MESSAGE_LIMIT = 20
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "usage.db")
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")


# ---------------------------------------------------------------------------
# Usage tracking (SQLite)
# ---------------------------------------------------------------------------

def _init_db():
    """Create the usage table if it does not exist."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS usage "
        "(username TEXT, date TEXT, message_count INTEGER, "
        "PRIMARY KEY(username, date))"
    )
    conn.commit()
    conn.close()

def _get_usage(username: str) -> int:
    """Return how many messages the user has sent today."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT message_count FROM usage WHERE username = ? AND date = ?",
        (username, date.today().isoformat()),
    ).fetchone()
    conn.close()
    return row[0] if row else 0

def _increment_usage(username: str) -> int:
    """Add 1 to today's count and return the new total."""
    conn = sqlite3.connect(DB_PATH)
    today = date.today().isoformat()
    row = conn.execute(
        "SELECT message_count FROM usage WHERE username = ? AND date = ?",
        (username, today),
    ).fetchone()
    if row:
        new_count = row[0] + 1
        conn.execute(
            "UPDATE usage SET message_count = ? WHERE username = ? AND date = ?",
            (new_count, username, today),
        )
    else:
        new_count = 1
        conn.execute(
            "INSERT INTO usage (username, date, message_count) VALUES (?, ?, ?)",
            (username, today, new_count),
        )
    conn.commit()
    conn.close()
    return new_count

_init_db()


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    """Load or create the auth config file."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH) as f:
            return yaml.safe_load(f)
    config = {
        "credentials": {"usernames": {}},
        "cookie": {
            "name": "travel_planner_auth",
            "key": "travel_planner_secret_key_change_me",
            "expiry_days": 30,
        },
    }
    _save_config(config)
    return config

def _save_config(config: dict):
    """Write config back to YAML."""
    with open(CONFIG_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


# ---------------------------------------------------------------------------
# PDF export function
# ---------------------------------------------------------------------------

def generate_pdf(messages: list[dict]) -> bytes:
    """Generate a PDF from the conversation history."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.colors import HexColor
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=25*mm, rightMargin=25*mm,
        topMargin=25*mm, bottomMargin=20*mm,
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "TripTitle", parent=styles["Title"],
        fontSize=22, textColor=HexColor("#1d4ed8"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "TripSubtitle", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#64748b"),
        spaceAfter=16,
    )
    heading_style = ParagraphStyle(
        "DayHeading", parent=styles["Heading2"],
        fontSize=14, textColor=HexColor("#1e293b"),
        spaceBefore=14, spaceAfter=6,
        borderColor=HexColor("#1d4ed8"), borderWidth=0,
    )
    body_style = ParagraphStyle(
        "TripBody", parent=styles["Normal"],
        fontSize=10, leading=16, textColor=HexColor("#334155"),
    )
    bold_label_style = ParagraphStyle(
        "BoldLabel", parent=styles["Normal"],
        fontSize=10, leading=16, textColor=HexColor("#1e293b"),
    )
    user_style = ParagraphStyle(
        "UserMsg", parent=styles["Normal"],
        fontSize=10, textColor=HexColor("#1d4ed8"),
        spaceBefore=10, spaceAfter=4,
    )

    story = []

    # Title
    story.append(Paragraph("Travel Planner AI", title_style))
    story.append(Paragraph("Your personalised travel itinerary", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    story.append(Spacer(1, 10))

    # Build PDF from messages
    for msg in messages:
        if msg["role"] == "user":
            story.append(Paragraph(f"<b>You:</b> {_escape_html(msg['content'])}", user_style))
        else:
            content = msg["content"]
            # Parse markdown-style content into PDF paragraphs
            lines = content.split("\n")
            for line in lines:
                line = line.strip()
                if not line:
                    story.append(Spacer(1, 4))
                    continue

                # Headings (### Day 1 — ...)
                if line.startswith("### ") or line.startswith("## "):
                    clean = line.lstrip("#").strip()
                    story.append(Paragraph(_escape_html(clean), heading_style))
                # Bullet points (- **Morning:** ...)
                elif line.startswith("- ") or line.startswith("* "):
                    clean = line[2:].strip()  # Remove only "- " or "* " prefix
                    # Convert **text** to <b>text</b>
                    clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", clean)
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;{_escape_html_keep_tags(clean)}", body_style))
                else:
                    # Convert any remaining **bold** markers
                    clean = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
                    story.append(Paragraph(_escape_html_keep_tags(clean), body_style))

    # Footer
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=HexColor("#e2e8f0")))
    story.append(Paragraph("Generated by Travel Planner AI — powered by Groq + LangChain", subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


def _escape_html(text: str) -> str:
    """Escape HTML special characters."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _escape_html_keep_tags(text: str) -> str:
    """Escape HTML but keep <b> and </b> tags."""
    # Temporarily replace <b> tags
    text = text.replace("<b>", "BOLDOPEN").replace("</b>", "BOLDCLOSE")
    text = _escape_html(text)
    text = text.replace("BOLDOPEN", "<b>").replace("BOLDCLOSE", "</b>")
    return text


def _extract_maps_from_response(content: str) -> dict | None:
    """Parse the agent's markdown response to extract place names and build Google Maps links.

    Looks for patterns like:
        ### Day 1 — Title
        - **Morning:** Visit the Colosseum...
    """
    from urllib.parse import quote_plus

    lines = content.split("\n")
    destination = ""

    # Try to find destination from context
    for line in lines:
        m = re.search(r'(?:trip to|itinerary for|visiting|days? in)\s+([A-Z][a-zA-Z\s,]+)', line)
        if m:
            destination = m.group(1).strip().rstrip('!.,')
            break

    days = []
    current_day = None

    for line in lines:
        line = line.strip()

        # Match "### Day 1 — Title"
        day_match = re.match(r'^#{2,3}\s+Day\s+\d+\s*[—–\-]\s*(.+)', line)
        if day_match:
            if current_day:
                days.append(current_day)
            current_day = {"title": line.lstrip("#").strip(), "links": []}
            continue

        # Match "- **Morning:** ..." or "* **Morning:** ..."
        slot_match = re.match(r'^[-*]\s+\*\*(\w+?):\*\*\s+(.+)', line)
        if slot_match and current_day is not None:
            slot_name = slot_match.group(1)
            activity = slot_match.group(2)
            place = _extract_place_for_maps(activity)
            if place:
                query = f"{place} {destination}" if destination else place
                url = f"https://www.google.com/maps/search/{quote_plus(query)}"
                current_day["links"].append((slot_name, place, url))

    if current_day:
        days.append(current_day)

    if not days:
        return None
    return {"destination": destination, "days": days}


def _extract_place_for_maps(text: str) -> str:
    """Extract the key place/restaurant name from an activity line."""
    # "such as [PLACE]" pattern (often the most specific)
    m = re.search(r'such as\s+(?:the\s+)?([A-Z][^,\-—.]+)', text)
    if m:
        return ' '.join(m.group(1).strip().split()[:5])

    # "at [PLACE]" pattern (restaurants, venues)
    m = re.search(r'\bat\s+(?:the\s+)?(?:a\s+)?([A-Z][^,\-—.]+?)(?:\s+(?:to|for|and|where|which|serving|featuring)\b|\s*$)', text)
    if m:
        return ' '.join(m.group(1).strip().split()[:5])

    # "at [PLACE]" simpler fallback
    m = re.search(r'\bat\s+(?:the\s+)?(?:a\s+)?([A-Z][^,\-—.]+)', text)
    if m:
        return ' '.join(m.group(1).strip().split()[:4])

    # "Visit/Explore the [PLACE]" pattern — stop at connecting words
    m = re.search(r'(?:Visit|Explore|Tour|See|Walk|Stroll)\s+(?:the\s+)?(?:a\s+)?([A-Z][^,\-—.]+?)(?:\s+(?:to|for|and|where|which|dedicated|featuring|known|located|including)\b|\s*$)', text, re.IGNORECASE)
    if m:
        return ' '.join(m.group(1).strip().split()[:5])

    # "in the [AREA]" pattern for neighbourhood references
    m = re.search(r'\bin\s+(?:the\s+)?([A-Z][a-zA-Z\'\-]+(?:\s+[a-zA-Z\'\-]+)?)\s+(?:area|district|neighbourhood|neighborhood)', text)
    if m:
        return m.group(1).strip()

    # Fallback: longest capitalised proper noun
    proper_nouns = re.findall(r'(?:[A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+)*)', text)
    if proper_nouns:
        return max(proper_nouns, key=len)
    return ""


# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="✈ Travel Planner AI",
    page_icon="✈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Custom CSS – warm travel aesthetic with deep indigo + golden accents
# ---------------------------------------------------------------------------

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Background */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
}

/* Hero banner */
.hero {
    background: linear-gradient(135deg, #1d4ed8 0%, #7c3aed 50%, #db2777 100%);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    text-align: center;
}
.hero h1 {
    font-family: 'Playfair Display', serif;
    color: #fff;
    font-size: 2.4rem;
    margin: 0;
}
.hero p {
    color: rgba(255,255,255,0.85);
    font-size: 1.05rem;
    margin-top: .5rem;
}

/* Chat messages */
.user-msg {
    background: #1e40af;
    color: #e0f2fe;
    border-radius: 18px 18px 4px 18px;
    padding: 12px 18px;
    margin: 6px 0;
    max-width: 80%;
    margin-left: auto;
    font-size: .97rem;
}
.bot-msg {
    background: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 18px 18px 18px 4px;
    padding: 14px 18px;
    margin: 6px 0;
    max-width: 90%;
    font-size: .97rem;
    line-height: 1.6;
}

/* Tool call expander */
.tool-box {
    background: #0f172a;
    border: 1px solid #f59e0b44;
    border-left: 3px solid #f59e0b;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: 'Courier New', monospace;
    font-size: .82rem;
    color: #fde68a;
    white-space: pre-wrap;
    overflow-x: auto;
    max-height: 320px;
    overflow-y: auto;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0f172a;
    border-right: 1px solid #1e293b;
}
section[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}
section[data-testid="stSidebar"] code {
    background: #334155 !important;
    color: #7dd3fc !important;
    padding: 2px 6px !important;
    border-radius: 4px !important;
    font-size: 0.85rem !important;
}

/* Input */
.stTextInput input {
    background: #1e293b !important;
    color: #f1f5f9 !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}

/* Buttons */
.stButton button {
    background: linear-gradient(135deg, #1d4ed8, #7c3aed) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
}
.stButton button:hover {
    opacity: 0.9 !important;
}

/* Quick prompt chips */
.chip-row {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin: 10px 0 20px 0;
}

/* Scrollable chat area */
.chat-container {
    max-height: 520px;
    overflow-y: auto;
    padding: 4px 0;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

def _get_bot() -> TravelPlannerChatbot:
    """Lazy-initialise the chatbot using server-side API key."""
    if "bot" not in st.session_state:
        # Try st.secrets first (Streamlit Cloud), then env var (local dev)
        api_key = st.secrets.get("GROQ_API_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key:
            api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            return None  # type: ignore
        st.session_state["bot"] = TravelPlannerChatbot(api_key=api_key)
    return st.session_state["bot"]


if "messages" not in st.session_state:
    st.session_state["messages"] = []   # list of {"role", "content", "tool_calls"}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## ✈ Travel Planner AI")
    st.markdown("*Powered by Groq (GPT-OSS 120B) + LangChain*")
    st.divider()

    api_key_input = None  # API key is now server-side

    # Show logged-in user info
    if st.session_state.get("authentication_status"):
        username = st.session_state.get("username", "")
        st.markdown(f"👤 Logged in as: **{username}**")
        used = _get_usage(username)
        remaining = max(0, DAILY_MESSAGE_LIMIT - used)
        st.markdown(f"💬 Messages today: **{used}/{DAILY_MESSAGE_LIMIT}**")
        st.progress(min(used / DAILY_MESSAGE_LIMIT, 1.0))
        if remaining == 0:
            st.warning("Daily limit reached. Come back tomorrow!")
        st.divider()

    st.divider()
    st.markdown("### 🛠 Available Tools")
    for tool_name, desc in [
        ("search_travel_info", "Live web search for blog recommendations"),
        ("generate_itinerary", "Day-by-day activity plan"),
        ("estimate_budget", "Full cost breakdown"),
        ("get_destination_tips", "Safety & etiquette tips"),
        ("get_weather_summary", "Weather & packing advice"),
    ]:
        st.markdown(f"**`{tool_name}`** — {desc}")

    st.divider()
    st.markdown("### 💡 Budget Levels")
    st.markdown("- **budget** – shoestring traveller\n- **mid-range** – comfortable explorer\n- **luxury** – premium experience")

    # Trip profile display
    bot = _get_bot()
    if bot and hasattr(bot, "get_profile"):
        profile = bot.get_profile()
        if profile:
            st.divider()
            st.markdown("### 🧳 Current Trip Profile")
            profile_labels = {
                "destination": "📍 Destination",
                "duration_days": "📅 Duration",
                "budget_level": "💰 Budget",
                "travelers": "👥 Travelers",
                "interests": "❤️ Interests",
                "climate": "🌡 Climate",
                "trip_style": "🎒 Style",
            }
            for key, label in profile_labels.items():
                if key in profile:
                    val = profile[key]
                    if isinstance(val, list):
                        val = ", ".join(str(v) for v in val)
                    st.markdown(f"{label}: **{val}**")

    st.divider()
    if st.button("🗑 Reset Conversation"):
        st.session_state["messages"] = []
        if "bot" in st.session_state:
            st.session_state["bot"].reset()
        st.rerun()


# ---------------------------------------------------------------------------
# Authentication gate
# ---------------------------------------------------------------------------

config = _load_config()

authenticator = stauth.Authenticate(
    config["credentials"],
    config["cookie"]["name"],
    config["cookie"]["key"],
    config["cookie"]["expiry_days"],
)

# Show login or register
if not st.session_state.get("authentication_status"):
    st.markdown("""
    <div class="hero">
      <h1>✈ Travel Planner AI</h1>
      <p>Your AI-powered travel assistant — plan trips to any city in the world!</p>
    </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        # login() also checks the browser re-authentication cookie, so a
        # returning user is logged back in automatically without a password.
        authenticator.login(location="main")
        if st.session_state.get("authentication_status") is False:
            st.error("Incorrect email or password.")

    with tab_register:
        try:
            # streamlit-authenticator >= 0.4:
            #  - pre_authorized takes a LIST of emails; omit it to let anyone register
            #  - merge_username_email=True uses the email as the username,
            #    so users sign in with their email address
            email, username, name = authenticator.register_user(
                location="main",
                merge_username_email=True,
                captcha=False,
            )
            if email:
                _save_config(config)
                st.success("Account created! You can now sign in with your email.")
        except Exception as e:
            st.error(str(e))

    # If the login form OR the cookie just authenticated the user,
    # rerun immediately so the app renders instead of the login screen.
    if st.session_state.get("authentication_status"):
        st.rerun()

    st.stop()  # Do not show the rest of the app

# If we get here, the user is authenticated
# Add logout button at the bottom of sidebar
with st.sidebar:
    authenticator.logout("🚪 Logout", location="main")


# ---------------------------------------------------------------------------
# Hero header
# ---------------------------------------------------------------------------

st.markdown("""
<div class="hero">
  <h1>✈ Travel Planner AI</h1>
  <p>Tell me where you want to go, for how long, and your budget — I'll plan your dream trip!</p>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Quick-start prompt buttons
# ---------------------------------------------------------------------------

QUICK_PROMPTS = [
    "Plan 7 days in Tokyo on a mid-range budget",
    "Budget trip to Bangkok for 5 days",
    "Luxury 10-day itinerary for Paris",
    "Estimate budget for 2 people, 5 days in Rome",
]

row1 = st.columns(2)
row2 = st.columns(2)
all_cols = [row1[0], row1[1], row2[0], row2[1]]
selected_quick = None
for col, prompt in zip(all_cols, QUICK_PROMPTS):
    with col:
        if st.button(prompt, key=f"q_{prompt}", use_container_width=True):
            selected_quick = prompt


# ---------------------------------------------------------------------------
# Chat display
# ---------------------------------------------------------------------------

chat_placeholder = st.container()

with chat_placeholder:
    if not st.session_state["messages"]:
        st.markdown("""
        <div class="bot-msg">
        👋 Hello! I'm your personal <strong>Travel Planner</strong>. I can:
        <ul>
          <li>🗓 Build a <em>day-by-day itinerary</em> for any destination</li>
          <li>💰 Estimate your <em>total trip budget</em></li>
          <li>💡 Share <em>local tips</em> on safety, culture & etiquette</li>
        </ul>
        Where would you like to travel? Tell me the destination, duration, and budget level!
        </div>
        """, unsafe_allow_html=True)

    for idx, msg in enumerate(st.session_state["messages"]):
        if msg["role"] == "user":
            st.markdown(f'<div class="user-msg">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
        else:
            # Render assistant message as proper markdown
            # Google Maps links are embedded directly in the text as [Name](url)
            st.markdown("✈ " + msg["content"])

            # Tool call raw data expander
            if msg.get("tool_calls"):
                with st.expander(f"⚙ {len(msg['tool_calls'])} tool call(s) — raw data", expanded=False):
                    for tc in msg["tool_calls"]:
                        st.markdown(f"**Tool:** `{tc['tool']}`")
                        try:
                            parsed = json.loads(tc["output"])
                            st.markdown(f'<div class="tool-box">{json.dumps(parsed, indent=2)}</div>', unsafe_allow_html=True)
                        except Exception:
                            st.markdown(f'<div class="tool-box">{tc["output"]}</div>', unsafe_allow_html=True)

            # Per-trip PDF export button
            try:
                # Build a mini message list: the user prompt + this assistant reply
                user_msg = None
                for prev in reversed(st.session_state["messages"][:idx]):
                    if prev["role"] == "user":
                        user_msg = prev
                        break
                pdf_msgs = []
                if user_msg:
                    pdf_msgs.append(user_msg)
                pdf_msgs.append(msg)

                pdf_bytes = generate_pdf(pdf_msgs)
                st.download_button(
                    label="📄 Export this plan to PDF",
                    data=pdf_bytes,
                    file_name=f"travel_plan_{idx}.pdf",
                    mime="application/pdf",
                    key=f"pdf_{idx}",
                )
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

st.markdown("---")
col_input, col_btn = st.columns([5, 1])
with col_input:
    user_input = st.text_input(
        "Message",
        value=selected_quick or "",
        placeholder="e.g. Plan a 7-day trip to Kyoto on a mid-range budget…",
        label_visibility="collapsed",
        key="user_input_field",
    )
with col_btn:
    send = st.button("Send ✈", use_container_width=True)


# ---------------------------------------------------------------------------
# Handle send
# ---------------------------------------------------------------------------

def _handle_message(message: str) -> None:
    if not message.strip():
        return

    # Check daily usage limit
    username = st.session_state.get("username", "anonymous")
    used = _get_usage(username)
    if used >= DAILY_MESSAGE_LIMIT:
        st.warning(f"You've used all {DAILY_MESSAGE_LIMIT} messages for today. Come back tomorrow!")
        return

    bot = _get_bot()
    if bot is None:
        st.error("API key not configured. Please contact the admin.")
        return

    st.session_state["messages"].append({"role": "user", "content": message})

    with st.spinner("Planning your trip… ✈"):
        try:
            reply, tool_calls = bot.chat(message)
            _increment_usage(username)  # Count this message
        except Exception as exc:
            reply = f"Sorry, something went wrong: {exc}"
            tool_calls = []

    st.session_state["messages"].append({
        "role": "assistant",
        "content": reply,
        "tool_calls": tool_calls,
    })
    st.rerun()


if send and user_input:
    _handle_message(user_input)
elif selected_quick:
    _handle_message(selected_quick)