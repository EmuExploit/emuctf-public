FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S -g 10001 corporate && adduser -S -u 10001 -G corporate corporate
RUN pip install --no-cache-dir Flask==3.1.2 gunicorn==23.0.0
COPY common/__init__.py common/logrun.py common/mattermost.py common/sessions.py common/request_bodies.py common/upload_tokens.py /app/common/
COPY frontend/__init__.py frontend/app.py frontend/contact.py /app/frontend/
COPY frontend/templates /app/frontend/templates
COPY frontend/static /app/frontend/static
COPY common/static /app/frontend/static
COPY common/templates /app/shared-templates
RUN mkdir -p /app/bootstrap/fixtures && touch /app/bootstrap/__init__.py /app/bootstrap/fixtures/__init__.py
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/run/corporate
RUN mkdir -p /logs /tmp/corporate /tmp/corporate-web && chown -R corporate:corporate /logs /tmp/corporate /tmp/corporate-web
USER corporate
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"
CMD ["python", "common/logrun.py", "/logs/frontend.log", "gunicorn", "--config", "python:frontend.config", "frontend.app:app"]
