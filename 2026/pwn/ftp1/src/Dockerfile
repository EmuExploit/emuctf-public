FROM ubuntu:22.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 ca-certificates \
 && rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 -s /bin/bash ctf
RUN mkdir -p /home/ctf/chal/storage

COPY chal /home/ctf/chal
COPY flag1.txt /home/ctf/chal/storage
COPY 0days_ru.txt /home/ctf/chal/storage
COPY fakerolex.txt /home/ctf/chal/storage

COPY flag2.txt /

RUN chown -R root:root /home/ctf/chal /flag2.txt && \
    chmod 0555 /home/ctf/chal/chal && \
    chmod 0444 /home/ctf/chal/storage/flag1.txt \
              /home/ctf/chal/storage/0days_ru.txt \
              /home/ctf/chal/storage/fakerolex.txt \
              /flag2.txt

WORKDIR /home/ctf/chal

USER ctf
EXPOSE 1337
CMD ["./chal"]
