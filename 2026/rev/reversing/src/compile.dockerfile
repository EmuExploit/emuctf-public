FROM ubuntu:22.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gcc libc6-dev libssl-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
CMD ["gcc", "src.c", "-s", "-o", "chal"]
