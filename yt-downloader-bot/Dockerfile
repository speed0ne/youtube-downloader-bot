# Stage 1: grab pre-built telegram-bot-api binary
FROM aiogram/telegram-bot-api:latest AS bot-api

# Stage 2: actual add-on
ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    supervisor \
    libstdc++

# Copy pre-built binary from the aiogram image
COPY --from=bot-api /usr/local/bin/telegram-bot-api /usr/local/bin/telegram-bot-api

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY bot/ bot/
COPY supervisord.conf /etc/supervisord.conf
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
