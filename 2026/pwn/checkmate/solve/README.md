# pwn/checkmate

## Overview

`checkmate` pits the user against the stockfish chess engine, the user starting with the white pieces. This would potentially be winnable by using stockfish yourself, but the twist is that there's a 10-move limit, which is definitely not winnable against the engine.

## Bug

The bugs that can be abused to solve the challenge are an off-by-one check in `move_parse` and a lack of rank bounds check in the `piece_moves` "ray" checking loop.

```c
typedef struct {
    unsigned char from;
    unsigned char to;
    int promotion;
} Move;

int move_parse(const char *text, Move *move) {
  size_t length = strlen(text);
  if (length != 4 && length != 5)
    return 0;
  int from_file = tolower((unsigned char)text[0]) - 'a';
  int to_file = tolower((unsigned char)text[2]) - 'a';
  int from_rank = text[1] - '0';
  int to_rank = text[3] - '0';
  if (from_file < 0 || from_file >= 8 || to_file < 0 || to_file >= 8 ||
      from_rank < 0 || from_rank > 8 || to_rank < 0 || to_rank > 8)
    return 0;
  move->from = (from_rank - 1) * 8 + from_file;
  move->to = (to_rank - 1) * 8 + to_file;

// ...

static void piece_moves(Board *board, int from, Move moves[MAX_MOVES],
                        size_t *count) {
  static const int knights[8][2] = {{1, 2},   {2, 1},   {2, -1}, {1, -2},
                                    {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
  static const int rays[8][2] = {{1, 0}, {-1, 0}, {0, 1},  {0, -1},
                                 {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
    // ...

    for (int i = 0; i < 8; i++) {
      if ((kind == BISHOP && i < 4) || (kind == ROOK && i >= 4))
        continue;
      int f = file;
      unsigned char to = from;
      do {
        f += rays[i][0];
        if (f < 0 || f >= 8)
          break;
        to += rays[i][1] * 8 + rays[i][0];
        if (to == from)
          break;
        int occupied = board->squares[to];
        offer(board, moves, count, from, to, 0);
        if (occupied || kind == KING)
          break;
      } while (1);
```

The 2 Bugs are:

- The parser erroneously allows the user to specify a rank of `0` which is invalid for a chess game.
- The `piece_moves` function checks the file is within the board bounds, but doesn't check the rank.

The `Move` structure's `from` and `to` members are of type `unsigned char` which is a single byte type. When `move->from` is calculated for a rank of `0`, it underflows and ends up out of bounds of the board. The move then passes the parser, and the lack of `rank` bounds checking in `piece_moves` allows the move to actually occur.

The idea of the challenge is to abuse these bugs to capture the king using an out of bounds piece. In `engine.c` we can see stockfish only receives the 8x8 chess board, so out of bounds pieces will be exempt from its analysis, allowing us to capture the king without it knowing.

The final piece of code that makes this work is in the checkmate condition:

```c
int board_check(const Board *board, int side) {
  for (int i = 0; i < 64; i++)
    if (board->squares[i] == side * KING)
      return attacked(board, i, -side);
  return 1;
}

static int finished(Board *board, Board history[HISTORY_LIMIT], size_t count) {
  Move moves[MAX_MOVES];
  if (!board_moves(board, moves)) {
    if (board_check(board, board->turn)) {
      if (board->turn == BLACK)
        award();
// ...
```

Although capturing the king is not a legal move in regular chess, if the challenge cannot find the king on the board, it treats it as being in check. The win condition will check whether any of black's legal moves will un-check the king, and since we captured it, that is impossible, so the state is treated as a checkmate, and we will be returned the flag.

## Exploit

The first step is to move our queen out of bounds using the move `d1d0`. Our queen is now off the board and can't be seen by stockfish. Because of the underflow, the queen will sit at `(0 - 1) * 8 + 3` which evaluates to `-5`, and when cast to an `unsigned char`, will be `251`. This ends up putting our queen at `board[251]`. The board is stored in the `.bss` section of the binary, and there is nothing else in the same page, so the queen is essentially now sitting in the middle of a bunch of unused null bytes. This is useful for moving it back to the board.

The next move will be to put our queen on the same file as stockfish's king, by playing `d0e0`. The queen will still be hidden from stockfish, and will now be at `board[252]`.

Finally, we can capture the king.

To check a move is valid, the `piece_moves` function will check a "ray" (some amount of squares in a direction) for every valid move direction, i.e. it will check if any pieces exist to block the path of the piece we are moving. The code to handle that for the queen is in `chess.c`:

```c
  static const int rays[8][2] = {{1, 0}, {-1, 0}, {0, 1},  {0, -1},
                                 {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
  // ...

  do {
        f += rays[i][0];
        if (f < 0 || f >= 8)
          break;
        to += rays[i][1] * 8 + rays[i][0];
        if (to == from)
          break;
        int occupied = board->squares[to];
        offer(board, moves, count, from, to, 0);
        if (occupied || kind == KING)
          break;
      } while (1);
```

The black king sits on square `60` and our queen sits on square `252`

Since our queen is directly "above" the king in memory `rays[3]` is the one which matters. The code will iterate over squares 252 -> 244 -> 236 -> ... -> 68 -> 60. Since squares 252 -> 68 are outside of the board after the `.bss` section in memory, and will be empty, so there is nothing blocking us from directly captured the king by playing our final move: `e0e8`

This can be automated easily with bash `{ printf 'd1d0\nd0e0\ne0e8\n'; sleep 5; } | nc <ip> <port>` which will return us the flag.
