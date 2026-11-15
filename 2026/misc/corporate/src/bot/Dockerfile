FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S -g 10001 corporate && adduser -S -u 10001 -G corporate corporate
RUN pip install --no-cache-dir websocket-client==1.8.0 Pillow==12.0.0
COPY common/__init__.py common/logrun.py common/mattermost.py common/support_channel.py /app/common/
COPY bot/__init__.py bot/bot.py bot/profile_images.py bot/recovery.py bot/support_chat.py bot/health.py bot/dispatcher.py bot/delivery.py bot/routing.py /app/bot/
RUN mkdir -p /app/bootstrap/fixtures && touch /app/bootstrap/__init__.py /app/bootstrap/fixtures/__init__.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/run/corporate
RUN mkdir -p /logs /tmp/corporate && chown -R corporate:corporate /logs /tmp/corporate
USER corporate
HEALTHCHECK --interval=10s --timeout=3s --retries=3 --start-period=30s CMD python -m bot.health
CMD ["python", "common/logrun.py", "/logs/bot.log", "python", "-m", "bot.bot"]
