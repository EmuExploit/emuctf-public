#define _POSIX_C_SOURCE 200809L

#include "chess.h"
#include "engine.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MOVE_LIMIT 10
#define HISTORY_LIMIT (MOVE_LIMIT * 2 + 1)

static Board board;

static void show_board(const Board *board) {
  static const char pieces[] = " PNBRQK";
  puts("");
  for (int rank = 7; rank >= 0; rank--) {
    printf("%d  ", rank + 1);
    for (int file = 0; file < 8; file++) {
      int piece = board->squares[rank * 8 + file];
      char symbol = piece ? pieces[abs(piece)] : '.';
      if (piece < 0)
        symbol = (char)tolower((unsigned char)symbol);
      printf("%c ", symbol);
    }
    puts("");
  }
  puts("\n   a b c d e f g h\n");
}

static int read_input(char *text, size_t capacity) {
  size_t length = 0;
  int invalid = 0;
  int byte;
  while ((byte = getchar()) != EOF && byte != '\n') {
    if (byte == '\r') {
      byte = getchar();
      if (byte != '\n' && byte != EOF)
        invalid = 1;
      while (byte != '\n' && byte != EOF)
        byte = getchar();
      break;
    }
    if (byte < 32 || byte > 126 || length + 1 >= capacity) {
      invalid = 1;
    } else {
      text[length++] = (char)byte;
    }
  }
  text[length] = '\0';
  if (byte == EOF && !length && !invalid)
    return 0;
  return invalid ? -1 : 1;
}

static void award(void) {
  puts("You win!");
  FILE *flag = fopen("flag.txt", "r");
  if (!flag) {
    puts("Flag unavailable. Contact an admin");
    return;
  }
  char buffer[256];
  while (fgets(buffer, sizeof(buffer), flag))
    fputs(buffer, stdout);
  fclose(flag);
  puts("");
}

static int finished(Board *board, Board history[HISTORY_LIMIT], size_t count) {
  Move moves[MAX_MOVES];
  if (!board_moves(board, moves)) {
    if (board_check(board, board->turn)) {
      if (board->turn == BLACK)
        award();
      else
        puts("You lose!");
    } else {
      puts("Stalemate. No flag!");
    }
    return 1;
  }
  if (board_insufficient(board) || board->halfmove >= 100) {
    puts("Draw. No flag!");
    return 1;
  }
  int repetitions = 0;
  for (size_t i = 0; i < count; i++)
    repetitions += board_same(board, &history[i]);
  if (repetitions >= 3) {
    puts("Draw by repetition. No flag!");
    return 1;
  }
  return 0;
}

int main(void) {
  setvbuf(stdin, NULL, _IONBF, 0);
  setvbuf(stdout, NULL, _IONBF, 0);
  Board history[HISTORY_LIMIT];
  size_t count = 1;
  board_init(&board);
  history[0] = board;
  puts("Can you checkmate stockfish in 10 moves?");
  puts("Enter moves as e2e4. Promotions: e7e8q. Type quit to leave.");
  if (!engine_start()) {
    puts("Stockfish unavailable.");
    return 1;
  }
  atexit(engine_stop);
  show_board(&board);
  int used = 0;
  while (used < MOVE_LIMIT) {
    char input[32];
    printf("Move %d/%d> ", used + 1, MOVE_LIMIT);
    int result = read_input(input, sizeof(input));
    if (!result || (result > 0 && strcmp(input, "quit") == 0))
      return 0;
    Move move;
    if (result < 0 || !move_parse(input, &move) || !board_play(&board, move)) {
      puts("Illegal move.");
      continue;
    }
    used++;
    history[count++] = board;
    if (finished(&board, history, count)) {
      show_board(&board);
      return 0;
    }
    if (used == MOVE_LIMIT) {
      show_board(&board);
      puts("Out of moves. No flag!");
      return 0;
    }
    if (!engine_move(&board, &move) || !board_play(&board, move)) {
      puts("Stockfish error.");
      return 1;
    }
    char text[6];
    move_format(move, text);
    printf("Stockfish: %s\n", text);
    history[count++] = board;
    show_board(&board);
    if (finished(&board, history, count))
      return 0;
    if (board_check(&board, WHITE))
      puts("Check.");
  }
  return 0;
}
