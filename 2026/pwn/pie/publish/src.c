#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

void banner() {
  puts(
  "           (            \n" \
  "            )           \n" \
  "       __..---..__      \n" \
  "   ,-='  /  |  \  `=-.  \n" \
  "  :--..___________..--; \n" \
  "   \.,_____________,./  \n"
  );

}

void setup() {
  setvbuf(stdout, NULL, _IONBF, 0);
  setvbuf(stderr, NULL, _IONBF, 0);
}

void vuln() {
  banner();
  char buf[0x10];
  printf("Do you like pie?\n");
  read(0, buf, 0x20);
}

void win() {
  system("/bin/bash");
  exit(0);
}

int main(void) {
  setup();
  vuln();
  return 0;
}
