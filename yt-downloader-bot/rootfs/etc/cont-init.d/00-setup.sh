#!/usr/bin/with-contenv bashio

# Read options from Home Assistant
export BOT_TOKEN=$(bashio::config 'bot_token')
export TELEGRAM_API_ID=$(bashio::config 'telegram_api_id')
export TELEGRAM_API_HASH=$(bashio::config 'telegram_api_hash')

# Persist env vars for s6 services
printf "%s" "$BOT_TOKEN" > /var/run/s6/container_environment/BOT_TOKEN
printf "%s" "$TELEGRAM_API_ID" > /var/run/s6/container_environment/TELEGRAM_API_ID
printf "%s" "$TELEGRAM_API_HASH" > /var/run/s6/container_environment/TELEGRAM_API_HASH
printf "%s" "http://127.0.0.1:8081" > /var/run/s6/container_environment/LOCAL_API_URL

bashio::log.info "Configuration loaded"
