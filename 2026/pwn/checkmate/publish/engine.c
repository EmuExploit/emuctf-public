#define _POSIX_C_SOURCE 200809L

#include "engine.h"

#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
#ifdef __linux__
#include <sys/prctl.h>
#endif

#ifndef STOCKFISH_PATH
#define STOCKFISH_PATH "/usr/games/stockfish"
#endif

static volatile sig_atomic_t engine_pid = -1;
static int input_fd = -1;
static int output_fd = -1;
static char buffer[4096];
static size_t position;
static size_t available;

static int64_t milliseconds(void)
{
    struct timespec now;
    if (clock_gettime(CLOCK_MONOTONIC, &now) < 0)
        return -1;
    return (int64_t)now.tv_sec * 1000 + now.tv_nsec / 1000000;
}

static int send_command(const char *command)
{
    size_t length = strlen(command);
    while (length) {
        ssize_t written = write(input_fd, command, length);
        if (written < 0 && errno == EINTR)
            continue;
        if (written <= 0)
            return 0;
        command += written;
        length -= (size_t)written;
    }
    return 1;
}

static int read_line(char *line, size_t capacity, int64_t deadline)
{
    size_t length = 0;
    for (;;) {
        if (milliseconds() >= deadline)
            return 0;
        if (position == available) {
            int64_t remaining = deadline - milliseconds();
            if (remaining <= 0)
                return 0;
            struct pollfd descriptor = {output_fd, POLLIN, 0};
            int result = poll(&descriptor, 1, (int)remaining);
            if (result < 0 && errno == EINTR)
                continue;
            if (result <= 0)
                return 0;
            ssize_t received = read(output_fd, buffer, sizeof(buffer));
            if (received < 0 && errno == EINTR)
                continue;
            if (received <= 0)
                return 0;
            position = 0;
            available = (size_t)received;
        }
        char byte = buffer[position++];
        if (byte == '\n') {
            line[length] = '\0';
            return 1;
        }
        if (byte == '\r')
            continue;
        if (!byte || length + 1 >= capacity)
            return 0;
        line[length++] = byte;
    }
}

static int expect(const char *expected)
{
    char line[4096];
    int64_t deadline = milliseconds() + 10000;
    while (read_line(line, sizeof(line), deadline))
        if (strcmp(line, expected) == 0)
            return 1;
    return 0;
}

static void expire(int signal_number)
{
    (void)signal_number;
    if (engine_pid > 0)
        kill(engine_pid, SIGKILL);
    _exit(1);
}

void engine_stop(void)
{
    if (input_fd >= 0)
        close(input_fd);
    if (output_fd >= 0)
        close(output_fd);
    input_fd = output_fd = -1;
    pid_t pid = engine_pid;
    engine_pid = -1;
    if (pid > 0) {
        kill(pid, SIGKILL);
        while (waitpid(pid, NULL, 0) < 0 && errno == EINTR) {}
    }
}

int engine_start(void)
{
    int to_engine[2];
    int from_engine[2];
    if (pipe(to_engine) < 0)
        return 0;
    if (pipe(from_engine) < 0) {
        close(to_engine[0]);
        close(to_engine[1]);
        return 0;
    }
    pid_t parent = getpid();
    engine_pid = fork();
    if (engine_pid == 0) {
#ifdef __linux__
        if (prctl(PR_SET_PDEATHSIG, SIGKILL) < 0 || getppid() != parent)
            _exit(1);
#else
        (void)parent;
#endif
        if (dup2(to_engine[0], STDIN_FILENO) < 0 || dup2(from_engine[1], STDOUT_FILENO) < 0)
            _exit(1);
        int null_fd = open("/dev/null", O_WRONLY);
        if (null_fd < 0 || dup2(null_fd, STDERR_FILENO) < 0)
            _exit(1);
        close(null_fd);
        close(to_engine[0]);
        close(to_engine[1]);
        close(from_engine[0]);
        close(from_engine[1]);
        execl(STOCKFISH_PATH, STOCKFISH_PATH, (char *)NULL);
        _exit(1);
    }
    close(to_engine[0]);
    close(from_engine[1]);
    input_fd = to_engine[1];
    output_fd = from_engine[0];
    if (engine_pid < 0) {
        engine_stop();
        return 0;
    }
    position = available = 0;
    struct sigaction action;
    memset(&action, 0, sizeof(action));
    sigemptyset(&action.sa_mask);
    action.sa_handler = SIG_IGN;
    sigaction(SIGPIPE, &action, NULL);
    action.sa_handler = expire;
    sigaction(SIGALRM, &action, NULL);
    sigaction(SIGTERM, &action, NULL);
    sigaction(SIGINT, &action, NULL);
    alarm(300);
    if (!send_command("uci\n") || !expect("uciok") ||
        !send_command("setoption name Threads value 1\nsetoption name Hash value 16\n"
                      "setoption name Skill Level value 20\nsetoption name UCI_LimitStrength value false\n"
                      "ucinewgame\nisready\n") || !expect("readyok")) {
        engine_stop();
        return 0;
    }
    return 1;
}

int engine_move(const Board *board, Move *move)
{
    char fen[128];
    char command[192];
    char line[4096];
    if (!board_fen(board, fen, sizeof(fen)))
        return 0;
    int length = snprintf(command, sizeof(command), "position fen %s\ngo movetime 1000\n", fen);
    if (length < 0 || (size_t)length >= sizeof(command) || !send_command(command))
        return 0;
    int64_t deadline = milliseconds() + 15000;
    while (read_line(line, sizeof(line), deadline)) {
        if (strncmp(line, "bestmove ", 9) != 0)
            continue;
        char *token = line + 9;
        char *end = strchr(token, ' ');
        if (end)
            *end = '\0';
        return move_parse(token, move);
    }
    return 0;
}
