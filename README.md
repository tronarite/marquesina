# 🎬 Marquesina

Bot de Telegram que avisa de las novedades en la cartelera de un cine de
[CineCiudad](https://cineciudad.com). No usa librerías externas, solo Python 3
estándar.

## ¿Qué avisa?

| | Evento |
|---|---|
| 🆕 | Entra una película nueva en cartelera |
| 🎟️ | Se abre la venta anticipada de un estreno |
| ⭐ | Hay una función única, programada para un solo día |
| ⏳ | A una película le quedan pocos días en cartelera |

Cada aviso se manda una sola vez por película. La detección de "últimos días"
no se basa en un umbral fijo: la web de CineCiudad siempre muestra una ventana
móvil de varios días de sesiones, así que la última fecha visible está casi
siempre a pocos días de hoy para *cualquier* película activa. Marquesina
compara esa ventana día a día y solo avisa cuando deja de avanzar, que es la
señal real de que la película se va.

## Sigue el cine de Ceuta sin instalar nada

Esta instancia oficial vigila **Marina Cinemas 7 (Ceuta)**. Solo tienes que
hablarle al bot:

👉 **[@cineciudad_notif_bot](https://t.me/cineciudad_notif_bot)**

- `/start` — empieza a seguirlo
- `/stop` — deja de seguirlo
- `/ayuda` — repite la explicación de los avisos
- `/cine` — muestra qué cine vigila

## Monta tu propia instancia (otro cine, otra ciudad)

Marquesina está pensado para que cada persona lo despliegue con el cine de
CineCiudad que le interese, sin tocar el código.

### 1. Crea tu bot de Telegram

1. Abre Telegram y habla con **@BotFather**.
2. Envíale `/newbot` y sigue los pasos (nombre y username del bot).
3. Te dará un **token** con forma `123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`.
4. Copia `config.example.json` a `config.json` y pega el token en
   `telegram_bot_token`.

### 2. Elige tu cine

En [cineciudad.com](https://cineciudad.com) busca tu cine y copia la URL de su
cartelera (algo como `https://cineciudad.com/cine.php?id=...`). Pégala en
`cine_url` dentro de `config.json`, y pon el nombre de tu cine en `cine_name`
(se usa en los mensajes del bot).

```json
{
  "telegram_bot_token": "TU_TOKEN",
  "admin_chat_id": "",
  "cine_url": "https://cineciudad.com/cine.php?id=TU_ID_DE_CINE",
  "cine_name": "Tu cine",
  "last_chance_days": 3
}
```

`admin_chat_id` es opcional: si lo rellenas, recibirás un aviso ahí si el
scraping falla (por ejemplo, si la web cambia de estructura). Usa
`get_chat_id.py` para averiguar tu chat_id:

```
python3 get_chat_id.py
```

### 3. Probar

```
python3 monitor.py
```

La primera vez solo guarda la cartelera actual como línea base (no manda
avisos). A partir de la segunda ejecución, cualquier cambio real dispara un
aviso a quien siga el bot.

Puedes forzar una prueba borrando `data/seen_movies.json` y volviendo a correr
`python3 monitor.py`.

### 4. Seguir el bot

Con `bot.py` corriendo, cualquiera puede escribirle `/start` a tu bot para
suscribirse. Pruébalo tú mismo:

```
python3 bot.py
```

### 5. Automatizar con cron

```
*/30 * * * * /usr/bin/python3 /ruta/a/marquesina/monitor.py >> /ruta/a/marquesina/data/cron.log 2>&1
```

Notas:
- macOS puede pedir permiso de "Acceso completo al disco" para `cron`/Terminal
  en Ajustes del Sistema > Privacidad y Seguridad si no se ejecuta.
- Los logs quedan en `data/cron.log`.

### 6. Docker (recomendado)

Docker ejecuta el monitor mediante `crond` y un segundo proceso para los
comandos de Telegram; no hace falta instalar cron en el host.

```
docker compose up -d --build
```

Por defecto revisa cada 30 minutos. Cambia `CRON_SCHEDULE` en `compose.yaml`
con una expresión cron de cinco campos y reinicia el servicio.

```
docker compose logs -f
```

### 7. Dale tu propia identidad

Si quieres que tu instancia tenga su propio nombre visible en Telegram (en vez
de "Marquesina"), cámbialo con `/setname` en **@BotFather**; el username del
bot no hace falta tocarlo.

## Archivos

- `monitor.py` — script principal: scrapea la cartelera, detecta los 4
  eventos y notifica a los suscriptores.
- `bot.py` — gestiona los comandos `/start`, `/stop`, `/ayuda`, `/cine`.
- `get_chat_id.py` — ayuda a encontrar un chat_id (para `admin_chat_id`).
- `config.json` — token, cine y ajustes (no se sube a git, contiene tu token).
- `data/` — estado generado automáticamente: suscriptores, cartelera vista,
  histórico de fechas y avisos ya enviados.
- `compose.yaml` y `Dockerfile` — ejecución programada en Docker.

## Licencia

MIT — ver [LICENSE](LICENSE).
