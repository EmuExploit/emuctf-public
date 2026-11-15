#ifndef ENGINE_H
#define ENGINE_H

#include "chess.h"

int engine_start(void);
int engine_move(const Board *board, Move *move);
void engine_stop(void);

#endif
