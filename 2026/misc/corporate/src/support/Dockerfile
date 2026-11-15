FROM python:3.12-alpine
WORKDIR /app
RUN addgroup -S -g 10001 corporate && adduser -S -u 10001 -G corporate corporate
RUN mkdir -p /var/lib/corporate/submissions /scanner-run && chown -R corporate:corporate /var/lib/corporate /scanner-run
RUN pip install --no-cache-dir Flask==3.1.2 gunicorn==23.0.0 nh3==0.3.2
COPY common/__init__.py common/logrun.py common/sessions.py common/request_bodies.py common/upload_tokens.py /app/common/
COPY support/__init__.py support/app.py support/mail_screening.py support/support_mail.py support/yara_client.py support/admission.py support/auth.py support/mailbox.py support/models.py support/notifications.py support/public.py support/reviewer.py support/submission.py support/upload_access.py /app/support/
COPY support/templates /app/support/templates
COPY support/static /app/support/static
COPY common/static /app/support/static
COPY common/templates /app/shared-templates
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/app:/run/corporate
RUN mkdir -p /logs /tmp/corporate && chown -R corporate:corporate /logs /tmp/corporate
USER corporate
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)"
CMD ["python", "common/logrun.py", "/logs/support.log", "gunicorn", "--config", "python:support.config", "support.app:app"]
