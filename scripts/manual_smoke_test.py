"""
Manual, opt-in smoke test against the LIVE bot via the real Telegram API.

Not part of the automated pytest suite and not safe to run in CI - it uses
.env credentials and writes real rows to the live DB. As with chores-
assistant, a bot can't fake an inbound message to itself (sendMessage only
sends bot -> user, it never reaches the message handler), so this can only
verify the bot is reachable and send you a message to prompt a manual round
trip - it can't simulate you sending "Goodmorning" and assert the reply.

Usage: python scripts/manual_smoke_test.py
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN not set in .env")
        return
    if not Config.TELEGRAM_USER_ID:
        print("TELEGRAM_USER_ID not set in .env - send /start to the bot first")
        return

    url = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": Config.TELEGRAM_USER_ID,
        "text": "Smoke test: if you see this, the bot can send messages. "
                "Now send a real message like 'Goodmorning' from your phone "
                "and confirm you get a Logged reply.",
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        resp.read()
    print("Sent. Check your Telegram client, then send a real test message yourself.")


if __name__ == "__main__":
    main()
