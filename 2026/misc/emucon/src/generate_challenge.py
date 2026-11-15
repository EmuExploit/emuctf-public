#!/usr/bin/env python3
"""
Fill `length` slots with random letters (a-z, A-Z), underscores and braces in 3 colors,
hiding `text` (in order, case preserved) in a single randomly chosen color.
Includes an interactive curses mode and an optional AHK script generator.

Usage:
    python generate_challenge.py 40 "EMU{placeholder}" --answer --interactive --gen-ahk
"""
import argparse
import os
import random
import string
import sys

try:
    import curses
    CURSES_AVAILABLE = True
except ImportError:
    CURSES_AVAILABLE = False

ESC = "\x1b["
RESET = ESC + "0m"

PALETTE = [196, 200, 46]
NUM_COLORS = len(PALETTE)
CHARACTERS = string.ascii_lowercase + string.ascii_uppercase + "_{}"


def generate(length, text, rng):
    secret = rng.randint(1, NUM_COLORS)
    positions = sorted(rng.sample(range(length), len(text)))
    slots = {p: (secret, ch) for p, ch in zip(positions, text)}
    out = []
    for i in range(length):
        if i in slots:
            out.append(slots[i])
        else:
            out.append((rng.randint(1, NUM_COLORS), rng.choice(CHARACTERS)))
    return secret, out, set(positions)


def render(tokens, labels):
    if labels:
        return " ".join(f"[{c}:{ch}]" for c, ch in tokens)
    return "".join(f"{ESC}38;5;{PALETTE[c - 1]}m{ch}{RESET}" for c, ch in tokens)


def create_ahk_script(secret, tokens, secret_positions):
    """Generates an AHK script (Left arrow + Backspace) that deletes secret-colored decoy characters, keeping the real secret and all other colors."""
    length = len(tokens)
    target_indices = [i for i, (c, _) in enumerate(tokens) if c == secret and i not in secret_positions]
    target_indices.sort(reverse=True)

    actions = []
    curr_pos = length
    for i in target_indices:
        left_steps = curr_pos - (i + 1)
        if left_steps > 0:
            actions.append(f"    SendInput, {{Left {left_steps}}}")
        actions.append("    SendInput, {Backspace}")
        curr_pos = i

    actions_str = "\n".join(actions)

    ahk_code = f"""; =====================================================================
; Auto-generated AHK Script to delete decoy characters in secret color #{secret} (keeps the real secret and all other colors)
; Press Ctrl + J to navigate with Left arrow and delete with Backspace.
; =====================================================================
#NoEnv
SendMode Input
SetWorkingDir %A_ScriptDir%

^j::
    ; Ensure cursor is at the very end of the text before running
    Sleep, 100
{actions_str}
    ToolTip, Secret color characters deleted!
    SetTimer, RemoveToolTip, 1500
return

RemoveToolTip:
    SetTimer, RemoveToolTip, Off
    ToolTip
return
"""
    filename = "solve.ahk"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(ahk_code)
    return filename


def run_interactive(tokens):
    """Interactive curses environment to navigate and delete characters with text wrapping and no headers/prompts."""
    if not CURSES_AVAILABLE:
        sys.exit("error: curses module is not available on this system (Windows requires 'pip install windows-curses').")

    # Must be set before curses initializes; removes the lag after Esc-prefixed key sequences.
    os.environ.setdefault("ESCDELAY", "25")

    def _main(stdscr):
        curses.curs_set(1)
        curses.start_color()
        curses.use_default_colors()

        for idx, color_val in enumerate(PALETTE, start=1):
            try:
                curses.init_pair(idx, color_val, -1)
            except curses.error:
                pass

        current_tokens = list(tokens)
        cursor_pos = len(current_tokens)

        while True:
            # erase() blanks the buffer without forcing a full terminal repaint (unlike clear()),
            # so curses only sends the diff and arrow-key movement doesn't flicker.
            stdscr.erase()
            height, width = stdscr.getmaxyx()

            usable_width = max(1, width)
            row_idx = 0
            col_idx = 0

            cursor_screen_y = 0
            cursor_screen_x = 0

            for i, (c_idx, ch) in enumerate(current_tokens):
                if col_idx >= usable_width:
                    row_idx += 1
                    col_idx = 0

                if i == cursor_pos:
                    cursor_screen_y = row_idx
                    cursor_screen_x = col_idx

                attr = curses.color_pair(c_idx) if 1 <= c_idx <= len(PALETTE) else 0
                if row_idx < height and col_idx < width:
                    try:
                        stdscr.addch(row_idx, col_idx, ch, attr)
                    except curses.error:
                        pass

                col_idx += 1

            if cursor_pos == len(current_tokens):
                if col_idx >= usable_width:
                    row_idx += 1
                    col_idx = 0
                cursor_screen_y = row_idx
                cursor_screen_x = col_idx

            try:
                stdscr.move(cursor_screen_y, cursor_screen_x)
            except curses.error:
                pass

            stdscr.refresh()

            key = stdscr.getch()

            if key in (ord('q'), ord('Q')):
                break
            elif key in (curses.KEY_LEFT, ord('h')):
                if cursor_pos > 0:
                    cursor_pos -= 1
            elif key in (curses.KEY_RIGHT, ord('l')):
                if cursor_pos < len(current_tokens):
                    cursor_pos += 1
            elif key in (curses.KEY_BACKSPACE, 127, 8):
                if cursor_pos > 0:
                    del current_tokens[cursor_pos - 1]
                    cursor_pos -= 1
            elif key in (curses.KEY_DC,):
                if cursor_pos < len(current_tokens):
                    del current_tokens[cursor_pos]



    curses.wrapper(_main)


def main():
    ap = argparse.ArgumentParser(description="Embed text into random colored slots with interactive curses mode.")
    ap.add_argument("length", nargs="?", type=int)
    ap.add_argument("text", nargs="?")
    ap.add_argument("--labels", action="store_true", help="debug: print [color:char] tokens")
    ap.add_argument("--answer", action="store_true", help="print the secret color")
    ap.add_argument("--gen-ahk", action="store_true", help="generate a companion AHK script file")
    ap.add_argument("-i", "--interactive", action="store_true", help="launch interactive curses environment")
    ap.add_argument("--seed", type=int, help="reproducible output")
    args = ap.parse_args()

    length = args.length if args.length is not None else int(input("length: "))
    text = args.text if args.text is not None else input("text: ")

    if not all(c in CHARACTERS for c in text):
        sys.exit("error: text must contain only letters, underscores, and braces ({ })")
    if length < len(text):
        sys.exit(f"error: length ({length}) must be >= len(text) ({len(text)})")

    os.system("")
    rng = random.Random(args.seed)
    secret, tokens, secret_positions = generate(length, text, rng)

    if args.gen_ahk:
        create_ahk_script(secret, tokens, secret_positions)

    if not args.interactive:
        print(render(tokens, args.labels))
        if args.answer:
            print(f"secret color: {secret}")
    else:
        if args.answer:
            print(f"[Info] Secret color is: {secret}")
        run_interactive(tokens)


if __name__ == "__main__":
    main()