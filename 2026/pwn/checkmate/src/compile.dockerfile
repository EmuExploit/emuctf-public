FROM --platform=linux/amd64 ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends gcc libc6-dev python3 stockfish && rm -rf /var/lib/apt/lists/*
WORKDIR /app
CMD ["gcc", "-O0", "-std=c11", "-Wall", "-Wextra", "-Wpedantic", "-Werror", "-fPIE", "-pie", "-Wl,-z,relro,-z,now", "engine.c", "chess.c", "src.c", "-o", "chal"]
