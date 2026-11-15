FROM python:3.12-alpine
RUN apk add --no-cache yara libarchive file \
    && pip install --no-cache-dir libarchive-c==5.3 \
    && addgroup -S -g 10001 scanner && adduser -S -u 10001 -G scanner scanner
RUN mkdir /scanner-run && chown scanner:scanner /scanner-run
WORKDIR /scanner
COPY scanner/__init__.py scanner/worker.py /scanner/scanner/
COPY common/logrun.py .
RUN mkdir /logs && chown scanner:scanner /logs
COPY scanner/yara /rules
ENV LIBARCHIVE=/usr/lib/libarchive.so.13 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/scanner:/run/corporate
USER scanner
CMD ["python", "logrun.py", "/logs/scanner.log", "python", "-m", "scanner.worker"]
