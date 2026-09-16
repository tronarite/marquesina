#!/usr/bin/env python3
"""Marquesina: avisa por Telegram de novedades en la cartelera de CineCiudad."""

import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
STATE_PATH = BASE_DIR / "data" / "seen_movies.json"
LAST_CHANCE_PATH = BASE_DIR / "data" / "last_chance_alerts.json"
SUBSCRIBERS_PATH = BASE_DIR / "data" / "subscribers.json"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)

MOVIE_BLOCK_PATTERN = re.compile(
    r'<div class="col-12 col-sm-4 col-lg-2 mb-5">(.*?)(?=<div class="col-12 col-sm-4 col-lg-2 mb-5">|$)',
    re.DOTALL,
)
MOVIE_PATTERN = re.compile(
    r'href="(pelicula\.php\?id=[a-f0-9]+)">.*?'
    r'<img class="card-img-top img-fluid" alt="([^"]*)"[^>]*src="([^"]*)"',
    re.DOTALL,
)
DATE_PATTERN = re.compile(r">[^<]*?(\d{1,2}) de ([A-Za-záéíóúñ]+) del (\d{4})<")
DAY_OPTION_PATTERN = re.compile(r'<option value="dia\d+">')
MONTHS = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
          "julio": 7, "agosto": 8, "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}


def log(msg: str) -> None:
    print(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        sys.exit(f"Falta {CONFIG_PATH}. Copia config.example.json a config.json y completalo.")
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    missing = [k for k in ("telegram_bot_token", "cine_url") if not config.get(k)]
    if missing:
        sys.exit(f"Completa estos campos en config.json: {', '.join(missing)}")
    return config


def cinema_name(config: dict) -> str:
    return config.get("cine_name") or "tu cine"


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def parse_movies(html: str) -> list[dict]:
    movies = []
    for block in MOVIE_BLOCK_PATTERN.findall(html):
        match = MOVIE_PATTERN.search(block)
        if not match:
            continue
        href, title, poster = match.groups()
        dates = [date(int(year), MONTHS[month.lower()], int(day)) for day, month, year in DATE_PATTERN.findall(block)]
        movies.append(
            {
                "title": title.strip(),
                "url": f"https://cineciudad.com/{href}",
                "poster": poster,
                "last_show_date": max(dates).isoformat() if dates else None,
                "advance_sale": "ventaanticipada" in block,
                "day_count": len(DAY_OPTION_PATTERN.findall(block)),
            }
        )
    return movies


def load_previous_movies() -> dict[str, dict] | None:
    if not STATE_PATH.exists():
        return None
    movies = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    return {m["title"]: m for m in movies}


def save_state(movies: list[dict]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(movies, ensure_ascii=False, indent=2), encoding="utf-8")


def load_last_chance_alerts() -> dict[str, str]:
    if not LAST_CHANCE_PATH.exists():
        return {}
    return json.loads(LAST_CHANCE_PATH.read_text(encoding="utf-8"))


def save_last_chance_alerts(alerts: dict[str, str]) -> None:
    LAST_CHANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAST_CHANCE_PATH.write_text(json.dumps(alerts, ensure_ascii=False, indent=2), encoding="utf-8")


def movies_now_showing(movies: list[dict], previous_movies: dict[str, dict]) -> list[dict]:
    """Peliculas ya conocidas que estaban en venta anticipada y acaban de pasar a cartelera normal."""
    return [
        m for m in movies
        if m["title"] in previous_movies
        and previous_movies[m["title"]].get("advance_sale")
        and not m["advance_sale"]
    ]


def remaining_days(movie: dict) -> int | None:
    last_show_date = movie.get("last_show_date")
    if not last_show_date:
        return None
    return (date.fromisoformat(last_show_date) - date.today()).days


def find_closing_soon(movies: list[dict], last_chance_days: int) -> list[dict]:
    """Detecta las peliculas que terminan antes que el resto de la cartelera.

    CineCiudad publica las sesiones por lotes, no dia a dia: la ultima fecha
    visible de la mayoria de peliculas se mueve a la vez (o se queda quieta
    varios dias seguidos) segun cuando se publique el siguiente lote. Por eso
    no sirve comparar la fecha de una pelicula contra si misma de un dia para
    otro (un lote sin publicar haria saltar el aviso para toda la cartelera a
    la vez). En su lugar, comparamos cada pelicula contra las demas: casi
    todas comparten la misma ultima fecha (el techo del lote actual); una
    pelicula que se queda corta frente a ese techo es la que de verdad
    termina antes.
    """
    candidates = [m for m in movies if m.get("last_show_date") and not m["advance_sale"]]
    if len(candidates) < 2:
        return []

    ceiling = Counter(m["last_show_date"] for m in candidates).most_common(1)[0][0]

    closing = []
    for movie in candidates:
        if movie["last_show_date"] < ceiling:
            remaining = remaining_days(movie)
            if remaining is not None and 0 <= remaining <= last_chance_days:
                closing.append(movie)
    return closing


def load_subscribers() -> list[str]:
    if not SUBSCRIBERS_PATH.exists():
        return []
    return json.loads(SUBSCRIBERS_PATH.read_text(encoding="utf-8"))


def save_subscribers(subscribers: list[str]) -> None:
    SUBSCRIBERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUBSCRIBERS_PATH.write_text(json.dumps(subscribers, ensure_ascii=False, indent=2), encoding="utf-8")


def add_subscriber(chat_id) -> bool:
    chat_id = str(chat_id)
    subscribers = load_subscribers()
    if chat_id in subscribers:
        return False
    subscribers.append(chat_id)
    save_subscribers(subscribers)
    return True


def remove_subscriber(chat_id) -> bool:
    chat_id = str(chat_id)
    subscribers = load_subscribers()
    if chat_id not in subscribers:
        return False
    subscribers.remove(chat_id)
    save_subscribers(subscribers)
    return True


def telegram_request(token: str, method: str, payload: dict) -> dict:
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/{method}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result


def send_telegram_photo(token: str, chat_id: str, photo_url: str, caption: str) -> None:
    telegram_request(token, "sendPhoto", {"chat_id": chat_id, "photo": photo_url, "caption": caption})


def send_telegram_message(token: str, chat_id: str, text: str) -> None:
    telegram_request(token, "sendMessage", {"chat_id": chat_id, "text": text})


def broadcast_photo(config: dict, photo_url: str, caption: str) -> None:
    token = config["telegram_bot_token"]
    subscribers = load_subscribers()
    if not subscribers:
        return
    blocked = []
    for chat_id in subscribers:
        try:
            send_telegram_photo(token, chat_id, photo_url, caption)
        except urllib.error.HTTPError as exc:
            if exc.code == 403:
                blocked.append(chat_id)
                log(f"Suscriptor {chat_id} bloqueo el bot, se quita de la lista.")
            else:
                log(f"Error al notificar a {chat_id}: {exc}")
        except Exception as exc:
            log(f"Error al notificar a {chat_id}: {exc}")
    if blocked:
        save_subscribers([c for c in subscribers if c not in blocked])


def notify_admin(config: dict, text: str) -> None:
    admin_chat_id = config.get("admin_chat_id")
    if not admin_chat_id:
        return
    try:
        send_telegram_message(config["telegram_bot_token"], admin_chat_id, text)
    except Exception as exc:
        log(f"No se pudo avisar al administrador: {exc}")


def notify_new_movie(config: dict, movie: dict) -> None:
    caption = f"🆕 Nueva en cartelera\n{movie['title']}\n{movie['url']}"
    broadcast_photo(config, movie["poster"], caption)


def notify_advance_sale(config: dict, movie: dict) -> None:
    caption = (
        f"🎟️ Venta anticipada abierta\n{movie['title']}\n"
        f"Compra tus entradas antes de que se agoten las mejores sesiones.\n{movie['url']}"
    )
    broadcast_photo(config, movie["poster"], caption)


def notify_single_showing(config: dict, movie: dict) -> None:
    caption = (
        f"⭐ Funcion unica: solo un dia\n{movie['title']}\n"
        f"Se proyecta unicamente el {movie['last_show_date']}. No te la pierdas.\n{movie['url']}"
    )
    broadcast_photo(config, movie["poster"], caption)


def notify_last_chance(config: dict, movie: dict) -> None:
    caption = (
        f"⏳ Ultimos dias en cartelera\n{movie['title']}\n"
        f"Ultimos pases hasta el {movie['last_show_date']}.\n{movie['url']}"
    )
    broadcast_photo(config, movie["poster"], caption)


def main() -> None:
    config = load_config()
    cine_url = config["cine_url"]

    try:
        html = fetch_html(cine_url)
    except Exception as exc:
        log(f"Error al descargar la cartelera: {exc}")
        notify_admin(config, f"Marquesina no pudo descargar la cartelera de {cinema_name(config)}: {exc}")
        sys.exit(1)

    movies = parse_movies(html)
    if not movies:
        log("No se encontraron peliculas en la pagina (revisar si cambio el HTML).")
        notify_admin(config, "Marquesina no encontro peliculas en la pagina. Puede que la web haya cambiado.")
        sys.exit(1)

    previous_movies = load_previous_movies()

    if previous_movies is None:
        save_state(movies)
        log(f"Primera ejecucion: guardadas {len(movies)} peliculas como linea base (sin notificar).")
        return

    new_movies = [m for m in movies if m["title"] not in previous_movies]
    now_showing = movies_now_showing(movies, previous_movies)

    if new_movies or now_showing:
        for movie in now_showing:
            try:
                notify_new_movie(config, movie)
                log(f"Notificado estreno tras preventa: {movie['title']}")
            except Exception as exc:
                log(f"Error al notificar '{movie['title']}': {exc}")
        for movie in new_movies:
            try:
                if movie["advance_sale"]:
                    notify_advance_sale(config, movie)
                    log(f"Notificada venta anticipada: {movie['title']}")
                elif movie["day_count"] == 1:
                    notify_single_showing(config, movie)
                    log(f"Notificada funcion unica: {movie['title']}")
                else:
                    notify_new_movie(config, movie)
                    log(f"Notificada pelicula nueva: {movie['title']}")
            except Exception as exc:
                log(f"Error al notificar '{movie['title']}': {exc}")
    else:
        log(f"Sin cambios ({len(movies)} peliculas en cartelera).")

    titles = {m["title"] for m in movies}
    last_chance_alerts = {t: d for t, d in load_last_chance_alerts().items() if t in titles}

    for movie in find_closing_soon(movies, config.get("last_chance_days", 3)):
        if last_chance_alerts.get(movie["title"]) != movie["last_show_date"]:
            try:
                notify_last_chance(config, movie)
                last_chance_alerts[movie["title"]] = movie["last_show_date"]
                log(f"Aviso de ultimos dias: {movie['title']}")
            except Exception as exc:
                log(f"Error al avisar ultimos dias de '{movie['title']}': {exc}")

    save_last_chance_alerts(last_chance_alerts)
    save_state(movies)


if __name__ == "__main__":
    main()
