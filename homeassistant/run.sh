#!/bin/sh

# Read options from Home Assistant
CONFIG_PATH=/data/options.json

export BOT_TOKEN=$(jq -r '.bot_token' $CONFIG_PATH)
export TELEGRAM_API_ID=$(jq -r '.telegram_api_id' $CONFIG_PATH)
export TELEGRAM_API_HASH=$(jq -r '.telegram_api_hash' $CONFIG_PATH)
export LOCAL_API_URL="http://127.0.0.1:8081"

exec supervisord -c /etc/supervisord.conf
