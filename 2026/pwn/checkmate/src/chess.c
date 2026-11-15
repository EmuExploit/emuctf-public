#include "chess.h"

#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int inside(int file, int rank) {
  return file >= 0 && file < 8 && rank >= 0 && rank < 8;
}

static int side_of(int piece) { return (piece > 0) - (piece < 0); }

void board_init(Board *board) {
  static const int back[] = {ROOK, KNIGHT, BISHOP, QUEEN,
                             KING, BISHOP, KNIGHT, ROOK};
  memset(board, 0, sizeof(*board));
  for (int file = 0; file < 8; file++) {
    board->squares[file] = back[file];
    board->squares[8 + file] = PAWN;
    board->squares[48 + file] = -PAWN;
    board->squares[56 + file] = -back[file];
  }
  board->turn = WHITE;
  board->castling = 15;
  board->ep = -1;
  board->fullmove = 1;
}

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
  move->promotion = 0;
  if (length == 5) {
    switch (tolower((unsigned char)text[4])) {
    case 'q':
      move->promotion = QUEEN;
      break;
    case 'r':
      move->promotion = ROOK;
      break;
    case 'b':
      move->promotion = BISHOP;
      break;
    case 'n':
      move->promotion = KNIGHT;
      break;
    default:
      return 0;
    }
  }
  return 1;
}

void move_format(Move move, char text[6]) {
  static const char pieces[] = " pnbrqk";
  text[0] = (char)('a' + (move.from & 7));
  text[1] = (char)('1' + (move.from >> 3));
  text[2] = (char)('a' + (move.to & 7));
  text[3] = (char)('1' + (move.to >> 3));
  text[4] = move.promotion ? pieces[move.promotion] : '\0';
  text[5] = '\0';
}

static int attacked(const Board *board, int square, int by) {
  int file = square % 8;
  int rank = square / 8;
  for (int df = -1; df <= 1; df += 2) {
    if (inside(file + df, rank - by) &&
        board->squares[(rank - by) * 8 + file + df] == by * PAWN)
      return 1;
  }
  static const int knights[8][2] = {{1, 2},   {2, 1},   {2, -1}, {1, -2},
                                    {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
  for (int i = 0; i < 8; i++) {
    int f = file + knights[i][0];
    int r = rank + knights[i][1];
    if (inside(f, r) && board->squares[r * 8 + f] == by * KNIGHT)
      return 1;
  }
  static const int rays[8][2] = {{1, 0}, {-1, 0}, {0, 1},  {0, -1},
                                 {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
  for (int i = 0; i < 8; i++) {
    int f = file + rays[i][0];
    int r = rank + rays[i][1];
    int distance = 1;
    while (inside(f, r)) {
      int piece = board->squares[r * 8 + f];
      if (piece) {
        if (side_of(piece) == by) {
          int kind = abs(piece);
          if (kind == QUEEN || (i < 4 && kind == ROOK) ||
              (i >= 4 && kind == BISHOP) || (distance == 1 && kind == KING))
            return 1;
        }
        break;
      }
      f += rays[i][0];
      r += rays[i][1];
      distance++;
    }
  }
  return 0;
}

int board_check(const Board *board, int side) {
  for (int i = 0; i < 64; i++)
    if (board->squares[i] == side * KING)
      return attacked(board, i, -side);
  return 1;
}

static void apply(Board *board, Move move) {
  int piece = board->squares[move.from];
  int captured = board->squares[move.to];
  int side = board->turn;
  if (abs(piece) == PAWN && move.to == board->ep && !captured) {
    board->squares[move.to - side * 8] = 0;
    captured = -side * PAWN;
  }
  board->squares[move.from] = 0;
  board->squares[move.to] = move.promotion ? side * move.promotion : piece;
  if (abs(piece) == KING) {
    board->castling &= side == WHITE ? ~3u : ~12u;
    if (move.to - move.from == 2) {
      board->squares[move.from + 1] = board->squares[move.from + 3];
      board->squares[move.from + 3] = 0;
    } else if (move.from - move.to == 2) {
      board->squares[move.from - 1] = board->squares[move.from - 4];
      board->squares[move.from - 4] = 0;
    }
  }
  static const int corners[] = {7, 0, 63, 56};
  for (int i = 0; i < 4; i++)
    if (move.from == corners[i] || move.to == corners[i])
      board->castling &= ~(1u << i);
  board->ep = abs(piece) == PAWN && abs(move.to - move.from) == 16
                  ? (move.from + move.to) / 2
                  : -1;
  board->halfmove = abs(piece) == PAWN || captured ? 0 : board->halfmove + 1;
  if (side == BLACK)
    board->fullmove++;
  board->turn = -side;
}

static void offer(Board *board, Move moves[MAX_MOVES], size_t *count, int from,
                  int to, int promotion) {
  Move move = {from, to, promotion};
  if (side_of(board->squares[move.to]) == board->turn)
    return;
  int side = board->turn;
  int source = board->squares[move.from];
  int target = board->squares[move.to];
  Board saved = *board;
  apply(board, move);
  int safe = !board_check(board, side);
  *board = saved;
  board->squares[move.from] = source;
  board->squares[move.to] = target;
  if (safe && *count < MAX_MOVES)
    moves[(*count)++] = move;
}

static void pawn_offer(Board *board, Move moves[MAX_MOVES], size_t *count,
                       int from, int to) {
  if (to / 8 == 0 || to / 8 == 7) {
    for (int kind = KNIGHT; kind <= QUEEN; kind++)
      offer(board, moves, count, from, to, kind);
  } else {
    offer(board, moves, count, from, to, 0);
  }
}

static void piece_moves(Board *board, int from, Move moves[MAX_MOVES],
                        size_t *count) {
  static const int knights[8][2] = {{1, 2},   {2, 1},   {2, -1}, {1, -2},
                                    {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
  static const int rays[8][2] = {{1, 0}, {-1, 0}, {0, 1},  {0, -1},
                                 {1, 1}, {1, -1}, {-1, 1}, {-1, -1}};
  int side = board->turn;
  int piece = board->squares[from];
  if (side_of(piece) != side)
    return;
  int kind = abs(piece);
  int file = from % 8;
  int rank = from / 8;
  if (kind == PAWN) {
    int r = rank + side;
    if (inside(file, r) && !board->squares[r * 8 + file]) {
      pawn_offer(board, moves, count, from, r * 8 + file);
      int start = side == WHITE ? 1 : 6;
      if (rank == start && !board->squares[(rank + side * 2) * 8 + file])
        offer(board, moves, count, from, (rank + side * 2) * 8 + file, 0);
    }
    for (int df = -1; df <= 1; df += 2) {
      if (!inside(file + df, r))
        continue;
      int to = r * 8 + file + df;
      int capture = side_of(board->squares[to]) == -side;
      int ep_rank = side == WHITE ? 4 : 3;
      int ep = rank == ep_rank && to == board->ep && !board->squares[to] &&
               board->squares[to - side * 8] == -side * PAWN;
      if (capture || ep)
        pawn_offer(board, moves, count, from, to);
    }
  } else if (kind == KNIGHT) {
    for (int i = 0; i < 8; i++) {
      int f = file + knights[i][0];
      int r = rank + knights[i][1];
      if (inside(f, r))
        offer(board, moves, count, from, r * 8 + f, 0);
    }
  } else {
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
    }
    int home = side == WHITE ? 4 : 60;
    unsigned rights = side == WHITE ? board->castling : board->castling >> 2;
    if (kind == KING && from == home && !board_check(board, side)) {
      if ((rights & 1) && board->squares[home + 3] == side * ROOK &&
          !board->squares[home + 1] && !board->squares[home + 2] &&
          !attacked(board, home + 1, -side))
        offer(board, moves, count, from, home + 2, 0);
      if ((rights & 2) && board->squares[home - 4] == side * ROOK &&
          !board->squares[home - 1] && !board->squares[home - 2] &&
          !board->squares[home - 3] && !attacked(board, home - 1, -side))
        offer(board, moves, count, from, home - 2, 0);
    }
  }
}

size_t board_moves(Board *board, Move moves[MAX_MOVES]) {
  size_t count = 0;
  for (int from = 0; from < 64; from++)
    piece_moves(board, from, moves, &count);
  return count;
}

int board_play(Board *board, Move move) {
  Move legal[MAX_MOVES];
  size_t count = 0;
  piece_moves(board, move.from, legal, &count);
  for (size_t i = 0; i < count; i++) {
    if (legal[i].from == move.from && legal[i].to == move.to &&
        legal[i].promotion == move.promotion) {
      apply(board, move);
      return 1;
    }
  }
  return 0;
}

int board_fen(const Board *board, char *text, size_t capacity) {
  char placement[80];
  char rights[5];
  char ep[3] = "-";
  size_t used = 0;
  static const char pieces[] = " PNBRQK";
  for (int rank = 7; rank >= 0; rank--) {
    int empty = 0;
    for (int file = 0; file < 8; file++) {
      int piece = board->squares[rank * 8 + file];
      if (!piece) {
        empty++;
        continue;
      }
      if (empty) {
        placement[used++] = (char)('0' + empty);
        empty = 0;
      }
      char symbol = pieces[abs(piece)];
      placement[used++] =
          piece > 0 ? symbol : (char)tolower((unsigned char)symbol);
    }
    if (empty)
      placement[used++] = (char)('0' + empty);
    if (rank)
      placement[used++] = '/';
  }
  placement[used] = '\0';
  used = 0;
  static const char castles[] = "KQkq";
  for (int i = 0; i < 4; i++)
    if (board->castling & (1u << i))
      rights[used++] = castles[i];
  if (!used)
    rights[used++] = '-';
  rights[used] = '\0';
  if (board->ep >= 0) {
    ep[0] = (char)('a' + board->ep % 8);
    ep[1] = (char)('1' + board->ep / 8);
    ep[2] = '\0';
  }
  int length = snprintf(text, capacity, "%s %c %s %s %d %d", placement,
                        board->turn == WHITE ? 'w' : 'b', rights, ep,
                        board->halfmove, board->fullmove);
  return length >= 0 && (size_t)length < capacity;
}

static int effective_ep(Board *board) {
  if (board->ep < 0)
    return -1;
  Move moves[MAX_MOVES];
  size_t count = board_moves(board, moves);
  for (size_t i = 0; i < count; i++)
    if (moves[i].to == board->ep &&
        abs(board->squares[moves[i].from]) == PAWN &&
        moves[i].from % 8 != moves[i].to % 8)
      return board->ep;
  return -1;
}

int board_same(Board *a, Board *b) {
  return a->turn == b->turn && a->castling == b->castling &&
         memcmp(a->squares, b->squares, sizeof(a->squares)) == 0 &&
         effective_ep(a) == effective_ep(b);
}

int board_insufficient(const Board *board) {
  int knights = 0;
  int bishops = 0;
  int colour = -1;
  for (int i = 0; i < 64; i++) {
    int kind = abs(board->squares[i]);
    if (!kind || kind == KING)
      continue;
    if (kind == KNIGHT) {
      knights++;
    } else if (kind == BISHOP) {
      int square_colour = (i % 8 + i / 8) % 2;
      if (colour >= 0 && colour != square_colour)
        return 0;
      colour = square_colour;
      bishops++;
    } else {
      return 0;
    }
  }
  return (bishops == 0 && knights <= 1) || (knights == 0);
}
