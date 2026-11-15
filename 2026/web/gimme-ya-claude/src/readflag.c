/*
 * readflag - setuid-root helper.
 *
 * The flag lives in /secret/flag.txt, owned by root and mode 0400, so the
 * unprivileged "app" user that runs the web app (and the claude child it
 * spawns) cannot read it directly. This binary is installed setuid-root, so
 * executing it prints the flag regardless of who runs it. Getting code
 * execution as "app" is therefore enough to capture the flag.
 *
 * The path is hard-coded, so this helper cannot be abused as an arbitrary
 * file-read primitive.
 */
#include <stdio.h>
#include <unistd.h>

int main(void) {
    /* Become fully root so the read succeeds under the setuid bit. */
    if (setgid(0) != 0 || setuid(0) != 0) {
        /* Not fatal: the effective uid from the setuid bit is enough to read. */
    }

    FILE *f = fopen("/secret/flag.txt", "r");
    if (!f) {
        perror("readflag: cannot open flag");
        return 1;
    }

    char buf[512];
    size_t n;
    while ((n = fread(buf, 1, sizeof buf, f)) > 0) {
        fwrite(buf, 1, n, stdout);
    }
    fclose(f);
    fputc('\n', stdout);
    return 0;
}
