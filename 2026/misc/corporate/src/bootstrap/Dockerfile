FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S -g 10001 corporate && adduser -S -u 10001 -G corporate corporate
COPY common/__init__.py common/logrun.py common/mattermost.py common/support_channel.py /app/common/
COPY bootstrap/__init__.py bootstrap/bootstrap.py bootstrap/channel_history.py bootstrap/mfa_archive.py bootstrap/noise.py bootstrap/player_permissions.py bootstrap/profile_images.py bootstrap/run.py bootstrap/discussion_history.py /app/bootstrap/
RUN mkdir -p /app/bootstrap/fixtures && touch /app/bootstrap/__init__.py /app/bootstrap/fixtures/__init__.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/run/corporate
RUN mkdir -p /logs /tmp/corporate /tmp/corporate-web && chown -R corporate:corporate /logs /tmp/corporate /tmp/corporate-web
USER corporate
CMD ["python", "common/logrun.py", "/logs/bootstrap.log", "python", "-m", "bootstrap.run"]
