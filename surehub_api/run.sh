#!/usr/bin/with-contenv bashio

EMAIL="$(bashio::config 'email')"
PASSWORD="$(bashio::config 'password')"
PORT="$(bashio::config 'port')"

export SUREHUB_EMAIL="${EMAIL}"
export SUREHUB_PASSWORD="${PASSWORD}"

export SUREHUB_ENDPOINT="https://app-api.production.surehub.io"
export SUREHUB_HOST="0.0.0.0"
export SUREHUB_PORT="${PORT}"
export SUREHUB_LOGLEVEL="info"

MQTT_HOST="$(bashio::services mqtt "host" 2>/dev/null || true)"
MQTT_PORT="$(bashio::services mqtt "port" 2>/dev/null || true)"
MQTT_USER="$(bashio::services mqtt "username" 2>/dev/null || true)"
MQTT_PASSWORD="$(bashio::services mqtt "password" 2>/dev/null || true)"

if [ -n "${MQTT_HOST}" ]; then
    export SUREHUB_MQTT_HOST="${MQTT_HOST}"
    export SUREHUB_MQTT_PORT="${MQTT_PORT:-1883}"
    export SUREHUB_MQTT_USER="${MQTT_USER}"
    export SUREHUB_MQTT_PASSWORD="${MQTT_PASSWORD}"
    export SUREHUB_MQTT_REFRESH_SECONDS="300"
fi

echo "SureHub config:"
echo "  endpoint=${SUREHUB_ENDPOINT}"
echo "  host=${SUREHUB_HOST}"
echo "  port=${SUREHUB_PORT}"
echo "  loglevel=${SUREHUB_LOGLEVEL}"
echo "  email set: yes"
echo "  password set: yes"

if [ -n "${SUREHUB_MQTT_HOST:-}" ]; then
    echo "  MQTT discovery: enabled"
    echo "  MQTT host: ${SUREHUB_MQTT_HOST}"
else
    echo "  MQTT discovery: unavailable"
fi

cd /app/surehub-api

exec /app/venv/bin/uvicorn custom_main:app --host "0.0.0.0" --port "${PORT}"
