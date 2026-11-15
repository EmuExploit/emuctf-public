#include <dirent.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <openssl/md5.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/sendfile.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <unistd.h>

#define DBG(fmt, ...)                                                          \
  do {                                                                         \
    fprintf(stderr, "[DBG]: " fmt "\n", ##__VA_ARGS__);                        \
  } while (0)

#define SERVER_PORT 1337
#define MAX_BACKLOG 50
#define REQ_BUF_LEN 0x100

unsigned char admin_hash[16] = {0x00, 0x40, 0x7d, 0xc8, 0x10, 0xd4, 0x38, 0x79,
                                0xe4, 0x0a, 0x42, 0x63, 0xab, 0x21, 0x40, 0x61};
char req_buf[REQ_BUF_LEN];

/*
 * GET <file>
 * PUT <file>
 * LIST <dir>
 */

typedef enum cmd_type {
  CMD_UNKNOWN,
  CMD_AUTH,
  CMD_GET,
  CMD_LIST,
  CMD_EXIT
} cmd_type_t;

typedef struct thread_arg {
  int client_fd;
  struct sockaddr_in client_addr;
} thread_arg_t;

unsigned char *md5(const void *data, size_t len) {
  if (data == NULL && len != 0)
    return NULL;
  unsigned char *out = (unsigned char *)malloc(MD5_DIGEST_LENGTH);
  if (!out)
    return NULL;
  MD5((const unsigned char *)data, len, out);
  return out;
}

ssize_t readline(int fd, char *buf, size_t len) {
  if (!buf || len == 0)
    return -1;

  size_t n = 0;

  while (n + 1 < len) {
    char c;
    ssize_t r = read(fd, &c, 1);
    if (r == 0)
      break;
    if (r < 0)
      return -1;

    if (c == '\n') {
      if (n > 0 && buf[n - 1] == '\r')
        n--;
      break;
    }

    buf[n++] = c;
  }

  buf[n] = '\0';
  return (ssize_t)n;
}
void send_str(int fd, char *msg) { (void)write(fd, msg, strlen(msg)); }

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

int valid_file(char *fname) {
  if (strstr(fname, "..") || fname[0] == '/') {
    return 0;
  }
  return 1;
}

bool handle_auth(int fd, char *password) {
  DBG("Handling password %s", password);
  char *hash = md5(password, strlen(password));

  if (!hash || strcmp(hash, admin_hash))
    goto err;

  return true;

err:
  send_str(fd, "INVALID PASSWORD");
  return false;
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
  if (file_fd < 0)
    goto err;

  if (fstat(file_fd, &st)) {
    goto err;
  }

  if (!S_ISREG(st.st_mode)) {
    goto err;
  }

  sendfile(fd, file_fd, NULL, st.st_size);

  return;
err:
  send_str(fd, "INVALID FILE");
  return;
}

void handle_list(int fd, char *req_path) {

  char path[0x100] = {0};
  struct stat st = {0};
  DIR *dir = NULL;

  DBG("Listing dir %s", req_path);

  if (!req_path || req_path[0] == '\0') {
    snprintf(path, sizeof(path), "storage");
  } else {
    snprintf(path, sizeof(path), "storage/%s", req_path);
  }

  if (stat(path, &st) != 0) {
    goto err;
  }
  if (!S_ISDIR(st.st_mode)) {
    goto err;
  }

  dir = opendir(path);
  if (!dir) {
    goto err;
  }

  struct dirent *de;
  while ((de = readdir(dir)) != NULL) {
    if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0)
      continue;

    send_str(fd, de->d_name);
    send_str(fd, "\n");
  }

  closedir(dir);
  return;

err:
  send_str(fd, "INVALID PATH");
  return;
}

void *handle_connection(void *thread_arg) {
  thread_arg_t *arg = (thread_arg_t *)thread_arg;
  char *cmd_arg = NULL;
  bool authed = false;

  while (1) {
    send_str(arg->client_fd, "> ");

    ssize_t n = readline(arg->client_fd, req_buf, REQ_BUF_LEN);
    if (n <= 0) {
      send_str(arg->client_fd, "FAILED TO READ");
      goto out;
    }

    cmd_type_t type = get_type_and_arg(req_buf, &cmd_arg);

    switch (type) {
    case CMD_AUTH:
      authed = handle_auth(arg->client_fd, cmd_arg);
      break;
    case CMD_GET:
      if (!authed) {
        send_str(arg->client_fd, "HACKING ATTEMPT");
        goto out;
      }
      handle_get(arg->client_fd, cmd_arg);
      break;
    case CMD_LIST:
      handle_list(arg->client_fd, cmd_arg);
      break;
    case CMD_EXIT:
      goto out;
    default:
      send_str(arg->client_fd, "UNKNOWN CMD");
      goto out;
    }
  }

out:
  close(arg->client_fd);
  free(arg);
}

int main(void) {
  int fd = -1;
  struct sockaddr_in addr = {.sin_family = AF_INET,
                             .sin_port = htons(SERVER_PORT),
                             .sin_addr.s_addr = INADDR_ANY};
  pthread_t tid;
  pthread_attr_t attr;

  fd = socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    perror("socket");
    return 1;
  }

  int opt = 1;
  if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
    perror("setsockopt(SO_REUSEADDR)");
    return 1;
  }

  if (setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &opt, sizeof(opt)) < 0) {
    perror("setsockopt(SO_REUSEPORT)");
    return 1;
  }

  if (bind(fd, (struct sockaddr *)&addr, sizeof(addr))) {
    perror("bind");
    return 1;
  }

  if (listen(fd, MAX_BACKLOG)) {
    perror("listen");
    return 1;
  }

  if (pthread_attr_init(&attr)) {
    perror("pthread_attr_init");
    return 1;
  }

  if (pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_DETACHED)) {
    perror("pthread_attr_setdetachstate");
    return 1;
  }

  while (1) {
    thread_arg_t *arg = malloc(sizeof(thread_arg_t));
    if (!arg) {
      perror("malloc");
      return 1;
    }

    socklen_t addrlen = sizeof(arg->client_addr);
    arg->client_fd = accept(fd, (struct sockaddr *)&arg->client_addr, &addrlen);

    if (arg->client_fd < 0) {
      perror("accept");
      free(arg);
      return 1;
    }

    if (pthread_create(&tid, &attr, handle_connection, (void *)arg)) {
      perror("pthread_create");
      free(arg);
      return 1;
    }
  }
  return 0;
}
