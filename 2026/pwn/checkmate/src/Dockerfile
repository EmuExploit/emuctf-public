FROM ghcr.io/downunderctf/docker-vendor/nsjail:ubuntu-24.04
RUN apt-get update && apt-get install -y --no-install-recommends stockfish && rm -rf /var/lib/apt/lists/*
ENV JAIL_CWD=/chal
ENV PORT=1337
ENV MAX_MEMORY=268435456
ENV MAX_PIDS=32
ENV TIME_LIMIT=300
ENV CPU_SHARES_MS=1000
COPY nsjail.cfg /home/ctf/nsjail.cfg
COPY --chmod=555 chal /home/ctf/chal/pwn
COPY --chmod=444 flag.txt /home/ctf/chal/flag.txt
EXPOSE 1337
