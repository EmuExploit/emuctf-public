FROM rust:1-bookworm
WORKDIR /app
CMD ["sh", "-c", "cargo build --release && cp target/release/easycrab chal"]
