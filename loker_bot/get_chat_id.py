"""One-time helper: prints your Telegram chat ID.

1. Send any message (e.g. "halo") to your bot in Telegram.
2. Run: TELEGRAM_BOT_TOKEN=xxx python3 -m loker_bot.get_chat_id
"""

import os
import sys
import urllib.error

from loker_bot.http import get_json

API_URL = "https://api.telegram.org/bot{token}/getUpdates"


def main() -> int:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("Set TELEGRAM_BOT_TOKEN first.")
        return 1
    try:
        updates = get_json(API_URL.format(token=token)).get("result", [])
    except urllib.error.HTTPError as error:
        if error.code in (401, 404):
            print("Token tidak valid. Salin ulang token lengkap dari @BotFather.")
        else:
            print(f"Telegram error: HTTP {error.code}")
        return 1
    chats = {
        str(u["message"]["chat"]["id"]): u["message"]["chat"].get("first_name", "")
        for u in updates if "message" in u
    }
    if not chats:
        print("No messages found. Send 'halo' to your bot in Telegram, then run again.")
        return 1
    for chat_id, name in chats.items():
        print(f"TELEGRAM_CHAT_ID={chat_id}  ({name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
