FROM ubuntu:24.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3 python3-venv socat && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv && /opt/venv/bin/pip install --no-cache-dir pycryptodome==3.23.0
RUN useradd -m ctf
COPY --chmod=555 run.sh /home/ctf/run.sh
COPY --chmod=444 server.py /home/ctf/server.py
COPY --chmod=444 flag.py /home/ctf/flag.py
RUN /opt/venv/bin/python -m py_compile /home/ctf/server.py /home/ctf/flag.py
USER ctf
WORKDIR /home/ctf
EXPOSE 1337
CMD ["socat", "TCP-LISTEN:1337,reuseaddr,fork", "EXEC:/home/ctf/run.sh,stderr"]
