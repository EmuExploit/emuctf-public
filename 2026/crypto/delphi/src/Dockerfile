FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends socat && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir pycryptodome
RUN useradd -m ctf
WORKDIR /home/ctf
COPY --chmod=444 src.py flag.txt ./
USER ctf
EXPOSE 1337
CMD ["socat", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:python3 -u src.py,stderr"]
