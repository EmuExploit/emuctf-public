# syntax=docker/dockerfile:1

FROM --platform=$BUILDPLATFORM tonistiigi/xx:1.7.0 AS xx

FROM --platform=$BUILDPLATFORM golang:1.27-alpine AS build

COPY --from=xx / /

ARG TARGETPLATFORM

RUN apk add --no-cache clang lld
RUN xx-apk add --no-cache gcc musl-dev
ENV CGO_ENABLED=1

COPY ./duckduckgo /build
RUN cd /build \
    && xx-go build -o /build/duckduckgo . \
    && xx-verify /build/duckduckgo

FROM postgres:16-alpine

RUN apk add --no-cache chromium

COPY --from=build /build/duckduckgo /app/duckduckgo
COPY ./duckduckgo/views /app/views
COPY ./duckduckgo/conf /app/conf
COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chmod -R a-w /app \
    && mkdir -p /user-scans

WORKDIR /app
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
