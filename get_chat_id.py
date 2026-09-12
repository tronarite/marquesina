#!/usr/bin/env python3
"""Ayuda a obtener un chat_id de Telegram, util para configurar 'admin_chat_id' en config.json."""

import json
import sys
import urllib.request
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    token = config.get("telegram_bot_token")
    if not token:
        sys.exit("Primero completa 'telegram_bot_token' en config.json")

    url = f"https://api.telegram.org/bot{token}/getUpdates"
    with urllib.request.urlopen(url, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))

    if not data.get("ok"):
        sys.exit(f"Error de Telegram: {data}")

    results = data.get("result", [])
    if not results:
        sys.exit(
            "No hay mensajes todavia. Abre tu bot en Telegram, envíale /start o cualquier "
            "mensaje, y vuelve a ejecutar este script."
        )

    seen = set()
    for update in results:
        message = update.get("message") or update.get("channel_post")
        if not message:
            continue
        chat = message["chat"]
        key = (chat["id"], chat.get("type"))
        if key in seen:
            continue
        seen.add(key)
        name = chat.get("title") or chat.get("username") or chat.get("first_name") or ""
        print(f"chat_id: {chat['id']}  tipo: {chat.get('type')}  nombre: {name}")


if __name__ == "__main__":
    main()
