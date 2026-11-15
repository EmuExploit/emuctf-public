#ifndef CHESS_H
#define CHESS_H

#include <stddef.h>

#define MAX_MOVES 256
#define WHITE 1
#define BLACK -1

enum { PAWN = 1, KNIGHT, BISHOP, ROOK, QUEEN, KING };

typedef struct {
    int turn;
    unsigned castling;
    int ep;
    int halfmove;
    int fullmove;
    int squares[64];
} Board;

typedef struct {
    unsigned char from;
    unsigned char to;
    int promotion;
} Move;

void board_init(Board *board);
int move_parse(const char *text, Move *move);
void move_format(Move move, char text[6]);
int board_check(const Board *board, int side);
size_t board_moves(Board *board, Move moves[MAX_MOVES]);
int board_play(Board *board, Move move);
int board_fen(const Board *board, char *text, size_t capacity);
int board_same(Board *a, Board *b);
int board_insufficient(const Board *board);

#endif
