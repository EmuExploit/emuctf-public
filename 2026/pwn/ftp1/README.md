# ftp1 and ftp2

`ftp1` owns the instanced FTP service. Its image contains both flags and listens
on port 1337. `ftp2/challenge.yml` uses the same per-team instance and the same
files from `ftp1/publish/` as player handouts. Both challenge entries publish
with `challengeIntegrationId: ftp1`.

The `AUTH` bug leads to the first flag in `storage/flag1.txt`. The race can
reach the second flag at `/flag2.txt`. `GET` still checks authentication for
each connection, so racing an unauthenticated connection cannot read the
first flag.

The supplied `chal` binary is kept unchanged in `src/` and `publish/`.
`src/compile.sh` can rebuild it from `src.c` for Linux amd64. The Docker image
uses the supplied binary by default.

Run locally with Docker:

```sh
cd src
docker compose -f compose.local.yml up --build -d
nc localhost 10001
```

The reference solution and writeup can be placed in `solve/`.

The hosted instance uses rCTF's TCP+SSL endpoint. Connect with the command
shown on the challenge page, such as `ncat --ssl <host> <port>`.
