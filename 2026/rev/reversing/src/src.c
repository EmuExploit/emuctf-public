#include <stdio.h>
#include <string.h>

char enc[] = {0x04, 0x00, 0x02, 0x3c, 0x31, 0x2c, 0x22,
              0x24, 0x32, 0x38, 0x20, 0x3e, 0x3c};

const char *code = "AMWGCIQVWNELA";

void reverse(char *str) {
  if (str == NULL || *str == '\0') {
    return;
  }

  int start = 0;
  int end = strlen(str) - 1;
  char temp;

  while (start < end) {
    temp = str[start];
    str[start] = str[end];
    str[end] = temp;
    start++;
    end--;
  }
}

int main(void) {
  setvbuf(stdout, NULL, _IONBF, 0);

  char input[14] = {};
  printf("Enter the code: ");
  fgets(input, sizeof(input), stdin);
  reverse(input);

  for (int i = 0; i < sizeof(input) - 1; i++) {
    if (input[i] != code[i]) {
      printf("Wrong code!\n");
      return 1;
    }
  }

  printf("Correct!\n");

  for (int i = 0; i < sizeof(enc); i++) {
    enc[i] ^= code[i];
  }

  printf("Flag: %s\n", enc);

  return 0;
}
