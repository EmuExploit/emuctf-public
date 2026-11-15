#!/usr/bin/env python3
import sys

LOAD_CONST_UNDEFINED, CALL2, RET = 0x94, 0x6F, 0x77

src = sys.argv[1] if len(sys.argv) > 1 else "../publish/main.hbc"
dst = sys.argv[2] if len(sys.argv) > 2 else "main.patched.hbc"

data = bytearray(open(src, "rb").read())
needle = bytes([LOAD_CONST_UNDEFINED, 0x00, CALL2, 0x01, 0x01, 0x02, 0x00, RET, 0x01])
off = data.find(needle)
assert off != -1 and data.find(needle, off + 1) == -1, "pattern not found exactly once"

arg_off = off + 6  # last operand of Call2
print(f"Call2 at {off + 2:#x}, patching arg byte at {arg_off:#x}: r0 -> r3")
data[arg_off] = 0x03
open(dst, "wb").write(data)
