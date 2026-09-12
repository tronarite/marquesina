#!/bin/sh
set -eu

: "${CRON_SCHEDULE:=*/30 * * * *}"
printf '%s cd /app && python monitor.py >> /proc/1/fd/1 2>&1\n' "$CRON_SCHEDULE" > /etc/crontabs/root
exec crond -f -l 2
