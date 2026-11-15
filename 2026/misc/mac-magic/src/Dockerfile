FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 socat && rm -rf /var/lib/apt/lists/*
RUN useradd -m ctf
COPY --chmod=555 run.sh /home/ctf/run.sh
COPY --chmod=444 src.py /home/ctf/src.py
COPY --chmod=444 flag.txt /home/ctf/flag.txt
RUN python3 -m py_compile /home/ctf/src.py
USER ctf
WORKDIR /home/ctf
EXPOSE 1337
CMD ["socat", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/home/ctf/run.sh,stderr"]
# TODO this chal doesnt need an instance, remove it.