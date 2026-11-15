# Hermes gets twitchy — writeup

**Flag:** `EMU{c4n7_chuck_this_into_gh1dr4}`

## Recon

```
$ file publish/main.hbc
publish/main.hbc: Hermes JavaScript bytecode, version 100
```

Hermes is React Native's JS engine, and `.hbc` is its compiled bytecode. The bytecode format changes between versions, so a tool only works if it supports the file's version:

| Tool | Result on v100 |
|---|---|
| `hbctool` (PyPI) | `AssertionError: The HBC version (100) is not supported.` (supports up to v85) |
| `hermes-compiler` npm `0.17.0` / `260318099.0.6` | `Wrong bytecode version. Expected 96 / 99 but got 100` |
| Hermes `static_h` HEAD (`BYTECODE_VERSION = 100`) | works |

The latest version of `ares` also does not support HBC version 100.

Build Hermes from source. This gives you the VM (`hermes`), the compiler and disassembler (`hermesc`), and Hermes' own bytecode tool `hbcdump`, which prints raw opcode bytes and file offsets:

```sh
git clone --depth 1 https://github.com/facebook/hermes.git && cd hermes
cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release -DHERMES_ENABLE_TEST_SUITE=OFF
ninja -C build hermes hermesc hbcdump
```

Running the file prints nothing useful:

```
$ hermes publish/main.hbc
undefined
```


## Method 1: static (guessy)

`strings` already shows most of what you need. Hermes stores all string literals in one blob and merges overlapping strings to save space. That's why `1c242b722731773e` and `emus > dogs` share an `e`, `636875636b5f` runs into `fromCharCode`, and so on:

```
1c242b722731773emus > dogs636875636b5fromCharCodecodeIVGVK63DGRXDOXY=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567Z[A-Za-z]\slice^=*$^[0-9a-fA-F]*$Stringlobaloguvf_vagbarkbork...TextDecoderUint8Array...
```

`hermesc -dump-bytecode publish/main.hbc` lists the string table cleanly, and the toplevel function references four decoder functions, `a`/`b`/`c`/`d`, one per literal, and joins the results:

```
LoadConstString   r4, "IVGVK63DGRXDOXY="    ; a(...)
LoadConstString   r4, "636875636b5f"        ; b(...)
LoadConstString   r4, "guvf_vagb"           ; c(...)
LoadConstString   r3, "1c242b722731773e"    ; d(...)
```

You can guess each encoding from how the literal looks and from the constants nearby:

| Literal | Hint | Decoding | Result |
|---|---|---|---|
| `IVGVK63DGRXDOXY=` | `A-Z2-7` with `=` padding; `ABCDEFGHIJKLMNOPQRSTUVWXYZ234567` is in the string table | base32 | `EMU{c4n7_` |
| `636875636b5f` | hex digits | hex | `chuck_` |
| `guvf_vagb` | letters only; `[A-Za-z]` regex and the constants 65/97/13/26 | ROT13 | `this_into` |
| `1c242b722731773e` | hex, but decodes to junk | hex, then XOR-crib with one byte | `_gh1dr4}` |

For the last one, brute-forcing a single XOR byte so the result ends in `}` gives exactly one key, 67 (`0x43`). This matches `LoadConstUInt8 r2, 67` / `BitXor` in `d`:

```
L4:
    GetByVal          r6, r7, r0
    BitXor            r3, r6, r2        ; r2 = 67
    PutByValLoose     r7, r0, r3
```

`solve/static.py` does the decoding:

```
$ python3 solve/static.py
EMU{c4n7_chuck_this_into_gh1dr4}
```

## Method 2: dynamic (patching)

The program already builds the flag, but its value is `void`ed before printing (`console.log(void (...))`). The end of the global function, from `hbcdump`:

```
$ hbcdump -objdump-disassemble -c "disassemble;quit" publish/main.hbc
...
00000532:  6f 03 05 00 03   Call2               %r3, %r5, %r0, %r3   ; r3 = d("1c24...")
00000537:  1e 03 04 03      Add                 %r3, %r4, %r3        ; r3 = a()+b()+c()+d()  <- flag
0000053b:  94 00            LoadConstUndefined  %r0
0000053d:  6f 01 01 02 00   Call2               %r1, %r1, %r2, %r0   ; console.log.call(console, r0)
00000542:  77 01            Ret                 %r1
```

The flag is computed into `r3`, then `void` turns it into `undefined` (`r0`), and `undefined` is what gets logged. `Call2`'s operands are `dst, callee, this, arg0`, one byte each. So rewrite `arg0` from `r0` to `r3`, which is the byte at `0x541`: `00` → `03`. The opcode numbers come from `include/hermes/BCGen/HBC/BytecodeList.def` (v100): `LoadConstUndefined = 0x94`, `Call2 = 0x6f`, `Ret = 0x77`.

`solve/patch.py` searches for the byte sequence `94 00 6f 01 01 02 00 77 01` (it occurs exactly once) and changes that one byte:

```
$ cd solve && python3 patch.py
Call2 at 0x53d, patching arg byte at 0x541: r0 -> r3
$ hermes main.patched.hbc
EMU{c4n7_chuck_this_into_gh1dr4}
```

