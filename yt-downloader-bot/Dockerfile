ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    supervisor \
    git \
    build-base \
    linux-headers \
    openssl-dev \
    zlib-dev

# Install telegram-bot-api from source
RUN apk add --no-cache cmake gperf && \
    cd /tmp && \
    git clone --recursive https://github.com/tdlib/telegram-bot-api.git && \
    cd telegram-bot-api && \
    mkdir build && cd build && \
    cmake -DCMAKE_BUILD_TYPE=Release .. && \
    cmake --build . --target install -j$(nproc) && \
    rm -rf /tmp/telegram-bot-api && \
    apk del cmake gperf build-base

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY bot/ bot/
COPY supervisord.conf /etc/supervisord.conf
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
