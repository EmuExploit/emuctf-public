FROM python:3.12-alpine
RUN addgroup -S -g 10001 corporate && adduser -S -u 10001 -G corporate corporate
WORKDIR /app
COPY notifications/relay.py .
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
USER corporate
HEALTHCHECK --interval=10s --timeout=3s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"
CMD ["python", "relay.py"]
