FROM python:3.14-alpine

WORKDIR /app
COPY monitor.py get_chat_id.py bot.py ./
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint
RUN chmod +x /usr/local/bin/docker-entrypoint && mkdir data

ENTRYPOINT ["docker-entrypoint"]
