"""
Travel Planner – Command-Line Interface
Run:  python cli.py
"""

from __future__ import annotations

import json
import os
import sys
import textwrap

# ---------------------------------------------------------------------------
# Optional: load a .env file automatically if python-dotenv is installed
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from core.chatbot import TravelPlannerChatbot

# ---------------------------------------------------------------------------
# Colour helpers (no external deps)
# ---------------------------------------------------------------------------

RESET  = "\033[0m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
GREY   = "\033[90m"
MAGENTA = "\033[95m"


def _banner() -> None:
    print(f"""
{CYAN}{BOLD}╔══════════════════════════════════════════╗
║   ✈  Travel Planner  •  AI Assistant   ║
╚══════════════════════════════════════════╝{RESET}
{GREY}Powered by Gemini (gemini-2.0-flash) via LangChain{RESET}
Type {YELLOW}"quit"{RESET} or {YELLOW}"exit"{RESET} to end  •  {YELLOW}"reset"{RESET} to start over  •  {YELLOW}"history"{RESET} to review
""")


def _print_tool_calls(tool_calls: list[dict]) -> None:
    if not tool_calls:
        return
    for tc in tool_calls:
        print(f"\n{MAGENTA}⚙  Tool called: {BOLD}{tc['tool']}{RESET}")
        if isinstance(tc["input"], dict):
            for k, v in tc["input"].items():
                print(f"{GREY}   {k}: {v}{RESET}")
        try:
            parsed = json.loads(tc["output"])
            pretty = json.dumps(parsed, indent=2)
            # Indent every line of the JSON block
            indented = "\n".join("   " + line for line in pretty.splitlines())
            print(f"{GREY}{indented}{RESET}")
        except (json.JSONDecodeError, TypeError):
            print(f"{GREY}   {tc['output']}{RESET}")


def _wrap(text: str, width: int = 88) -> str:
    """Wrap long lines while preserving existing newlines."""
    lines = []
    for paragraph in text.split("\n"):
        if paragraph.strip():
            lines.extend(textwrap.wrap(paragraph, width=width))
        else:
            lines.append("")
    return "\n".join(lines)


def main() -> None:
    _banner()

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(f"{YELLOW}GOOGLE_API_KEY not found in environment.{RESET}")
        api_key = input("Please enter your Google API key: ").strip()
        if not api_key:
            print("No API key provided. Exiting.")
            sys.exit(1)

    try:
        bot = TravelPlannerChatbot(api_key=api_key)
    except Exception as exc:
        print(f"Failed to initialise chatbot: {exc}")
        sys.exit(1)

    print(f"{GREEN}Assistant:{RESET} Hello! I'm your personal Travel Planner 🌍  "
          "Tell me where you'd like to go, for how long, and your budget level "
          "(budget / mid-range / luxury), and I'll start building your perfect trip!\n")

    while True:
        try:
            user_input = input(f"{CYAN}You:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye! Safe travels ✈")
            break

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in {"quit", "exit", "bye"}:
            print(f"\n{GREEN}Assistant:{RESET} Goodbye! Have an amazing trip! ✈🌟\n")
            break

        if lower == "reset":
            bot.reset()
            print(f"\n{GREEN}Assistant:{RESET} Conversation reset. Where would you like to explore? 🗺\n")
            continue

        if lower == "history":
            hist = bot.history
            if not hist:
                print(f"{GREY}(No conversation history yet){RESET}\n")
            else:
                for msg in hist:
                    role_label = f"{CYAN}You{RESET}" if msg["role"] == "user" else f"{GREEN}Assistant{RESET}"
                    print(f"{role_label}: {msg['content']}\n")
            continue

        print()  # breathing room

        try:
            reply, tool_calls = bot.chat(user_input)
        except Exception as exc:
            print(f"{YELLOW}Error communicating with the API: {exc}{RESET}\n")
            continue

        _print_tool_calls(tool_calls)
        print(f"\n{GREEN}Assistant:{RESET} {_wrap(reply)}\n")


if __name__ == "__main__":
    main()