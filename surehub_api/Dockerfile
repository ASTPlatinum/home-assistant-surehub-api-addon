ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:latest
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    python3 \
    py3-pip \
    git \
    curl \
    bash

WORKDIR /app

RUN git clone https://github.com/fabieu/surehub-api.git /app/surehub-api

WORKDIR /app/surehub-api

RUN python3 -m venv /app/venv \
    && /app/venv/bin/pip install --upgrade pip setuptools wheel \
    && /app/venv/bin/pip install --no-cache-dir .

COPY custom_main.py /app/surehub-api/custom_main.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]