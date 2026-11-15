FROM ubuntu:22.04
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends gcc libc6-dev libssl-dev && rm -rf /var/lib/apt/lists/*
WORKDIR /app
CMD ["gcc", "-O0", "-std=gnu11", "-Wall", "-Wextra", "-fPIE", "-pie", "-Wl,-z,relro,-z,now", "-pthread", "src.c", "-lcrypto", "-o", "chal"]
