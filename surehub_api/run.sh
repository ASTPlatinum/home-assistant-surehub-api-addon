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

echo "SureHub config:"
echo "  endpoint=${SUREHUB_ENDPOINT}"
echo "  host=${SUREHUB_HOST}"
echo "  port=${SUREHUB_PORT}"
echo "  loglevel=${SUREHUB_LOGLEVEL}"
echo "  email set: yes"
echo "  password set: yes"

cd /app/surehub-api

exec /app/venv/bin/uvicorn surehub_api.main:app --host "0.0.0.0" --port "${PORT}"