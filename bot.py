#!/usr/bin/env python3
"""Comandos de Telegram de Marquesina: alta y baja de suscriptores."""

import time

import monitor

HELP_TEXT = (
    "Marquesina te avisa de la cartelera de {cine}:\n\n"
    "🆕 Cuando entra una pelicula nueva\n"
    "🎟️ Cuando se abre la venta anticipada de un estreno\n"
    "⭐ Cuando hay una funcion unica de un solo dia\n"
    "⏳ Cuando a una pelicula le quedan pocos dias en cartelera\n\n"
    "Comandos: /start para seguir el bot, /stop para dejar de seguirlo, /cine para ver que cine vigila."
)


def reply(token: str, chat_id: int, text: str) -> None:
    monitor.send_telegram_message(token, chat_id, text)


def handle_message(config: dict, chat_id: int, text: str) -> None:
    token = config["telegram_bot_token"]
    command = text.strip().split(" ", 1)[0].split("@", 1)[0].lower()

    if command == "/start":
        added = monitor.add_subscriber(chat_id)
        intro = "Ya estas siguiendo Marquesina. " if added else "Ya estabas siguiendo Marquesina. "
        reply(token, chat_id, intro + HELP_TEXT.format(cine=monitor.cinema_name(config)))
    elif command == "/stop":
        removed = monitor.remove_subscriber(chat_id)
        text_out = "Dejaste de seguir Marquesina. No recibiras mas avisos." if removed else "No estabas siguiendo Marquesina."
        reply(token, chat_id, text_out)
    elif command in ("/ayuda", "/help"):
        reply(token, chat_id, HELP_TEXT.format(cine=monitor.cinema_name(config)))
    elif command == "/cine":
        reply(token, chat_id, f"Este bot vigila la cartelera de {monitor.cinema_name(config)}.")


def main() -> None:
    config = monitor.load_config()
    token = config["telegram_bot_token"]
    offset = None
    while True:
        try:
            payload = {"timeout": 25}
            if offset is not None:
                payload["offset"] = offset
            for update in monitor.telegram_request(token, "getUpdates", payload)["result"]:
                offset = update["update_id"] + 1
                message = update.get("message", {})
                chat_id, text = message.get("chat", {}).get("id"), message.get("text")
                if chat_id and text:
                    handle_message(config, chat_id, text)
        except Exception as exc:
            monitor.log(f"Error del bot: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
