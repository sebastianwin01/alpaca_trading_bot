"""Create a macOS LaunchAgent to run bot.py at 9:40 AM local, Mon–Fri.

Run this from ~/alpaca_trading_bot only AFTER checking bot.py in DRY_RUN mode.
Requires Mac logged in; does not run in cloud.
"""

from pathlib import Path
import plistlib

PROJECT = Path(__file__).resolve().parent
PYTHON = PROJECT / ".venv" / "bin" / "python"
BOT = PROJECT / "bot.py"
LABEL = "com.alpaca.sma520.paperbot"
AGENT_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOGS = PROJECT / "logs"

if not PYTHON.is_file() or not BOT.is_file():
    raise FileNotFoundError("Expected .venv/bin/python and bot.py in the project")

LOGS.mkdir(exist_ok=True)
AGENT_PATH.parent.mkdir(parents=True, exist_ok=True)

agent = {
    "Label": LABEL,
    "ProgramArguments": [str(PYTHON), "-u", str(BOT)],
    "WorkingDirectory": str(PROJECT),
    "StartCalendarInterval": [
        {"Weekday": weekday, "Hour": 9, "Minute": 40}
        for weekday in range(1, 6)
    ],
    "StandardOutPath": str(LOGS / "bot.log"),
    "StandardErrorPath": str(LOGS / "bot-error.log"),
    "RunAtLoad": False,
}

with AGENT_PATH.open("wb") as handle:
    plistlib.dump(agent, handle)

print("Created:", AGENT_PATH)
print("Runs 9:40 AM Monday–Friday, using the Mac's local timezone.")
print("To activate, run:")
print(f"launchctl bootstrap gui/$(id -u) '{AGENT_PATH}'")
print("Check logs with:")
print(f"tail -f '{LOGS / 'bot.log'}'")
