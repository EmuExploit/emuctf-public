# syntax=docker/dockerfile:1

FROM ruby:3.3-slim-bookworm
ARG TARGETARCH

RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu curl bash ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1001 -s /bin/bash app

USER app
WORKDIR /home/app

RUN arch="${TARGETARCH:-$(dpkg --print-architecture)}" \
    && case "$arch" in \
      amd64|x86_64) release_arch=linux-x64; \
        expected=dabafec82ca1319fa43d8be36a10fc61b1d11821cb98ad5df04ad95e199b8eed ;; \
      arm64|aarch64) release_arch=linux-arm64; \
        expected=a7e687fd1cb054d651c7588223de3786c99d4c682365e3c3ae1e59ce7f3a591f ;; \
      *) echo "unsupported architecture: $arch" >&2; exit 1 ;; \
    esac \
    && mkdir -p /home/app/.local/bin \
    && curl -fsSL \
      "https://downloads.claude.ai/claude-code-releases/2.1.319/${release_arch}/claude" \
      -o /home/app/.local/bin/claude \
    && echo "$expected  /home/app/.local/bin/claude" | sha256sum -c - \
    && chmod 0755 /home/app/.local/bin/claude

USER root

RUN ln -sf /home/app/.local/bin/claude /usr/local/bin/claude

WORKDIR /app

COPY Gemfile Gemfile.lock ./
COPY readflag.c /tmp/readflag.c

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential pkg-config libssl-dev libssl3 \
    && bundle config set --local without 'development test' \
    && (bundle install || { \
        cat /usr/local/bundle/extensions/*/*/puma-*/mkmf.log; \
        exit 1; \
    }) \
    && gcc -O2 -static -o /usr/local/bin/readflag /tmp/readflag.c \
    && rm -f /tmp/readflag.c \
    && apt-get purge -y --auto-remove \
        build-essential pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/* /usr/local/bundle/cache

COPY . .

COPY entrypoint.sh /entrypoint.sh

RUN chmod 0755 /entrypoint.sh \
    && chown root:root /usr/local/bin/readflag \
    && chmod 4755 /usr/local/bin/readflag \
    && mkdir -p /secret /tmp/home /app/tmp /app/log

ENV RAILS_ENV=production \
    PORT=8080 \
    HOME=/tmp/home

EXPOSE 8080

ENTRYPOINT ["/entrypoint.sh"]
