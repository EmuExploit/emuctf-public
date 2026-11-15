# Hermes gets angy — writeup

**Flag:** `EMU{y0u_c4n_b1nj4_bu7_g00d_luck_h0n357ly}`

## Recon

```
$ file main
main: ELF 64-bit LSB pie executable, x86-64, dynamically linked, ... not stripped
$ ldd main | grep -v /usr/lib
	libshermes_console.so => .../hermes/build/tools/shermes/libshermes_console.so
	libhermesvm.so => .../hermes/build/lib/libhermesvm.so
$ echo anything | ./main
Hash matched
```

It doesn't read any input. It just prints `Hash matched`, so the flag must be
built inside the program and only checked against a hash.

The imports (`_sh_init`, `_sh_ljs_call`, `_sh_ljs_get_by_id_rjs`, ...) and the
`s_function_info_table` / `s_strings` symbols show this is **Static Hermes**
(`shermes`). JavaScript was compiled to C and then to native code, and every JS
function became a C function named `_<index>_<jsName>`:

```
$ nm main | grep -E ' t _[0-9]+_' | grep -v cold
_0_global  _1_d  _2_e  _3_h  _4_j  _5_k  _6_m  _7_n  _8_o  _9_t  _10_v  _11_w
_12_x  _13_y  _14_a ... _22_u  _23_ac  _24_update  _25_digest  _26_i  _27__1_
```

The interesting strings are in the string table (`s_ascii_pool`):

```
roundKeys rounds Uint8Array update digest prototype fromHex
17b2811c20b4ac70   emuexp>skibidogs
9c0cf74c609fff9586 emusover roombas
f04e5ec98c0777be   emusbttrthnbears
d57eaffa809185ae67c4de0af1c6d7a3   hi - nullvoidptr
Hash matched  imul  fill  subarray  ...
```

So there are four hex ciphertexts and four 16-byte keys, along with
`update`/`digest`, which look like a hash object. The likely design is that
each ciphertext is decrypted and fed to `hash.update()`, so the plaintext
passes through `_24_update` as its argument. Reading the compiled code
statically is slow, because each JS operation becomes a call into the runtime
on NaN-boxed values. A breakpoint on `update` is enough.

## Static Hermes runtime internals for debugging

The binary loads `libhermesvm.so` from a Hermes build with DWARF, so gdb knows
the VM types (`SHRuntime`, `hermes::vm::JSTypedArrayBase`, ...). Run
`set language c++` before using them, because the frames in `main` have no
debug info. Three facts are enough to read JS values:

1. **Calling convention.** Every compiled function is
   `SHLegacyValue fn(SHRuntime *shr)`. Its prologue `_sh_enter()` takes the
   frame register as `frame = shr->stackPointer`. From
   `hermes/VMLayouts/sh_stack_frame_layout.h`, the frame slots are:
   `frame[-5]` = argc, `frame[-8]` = `this`, `frame[-9 - i]` = argument `i`.
   On a breakpoint at a function's entry, `rdi` is `shr`, so all arguments can
   be read. The return value comes back in `rax`.
2. **Values are NaN-boxed** (`sh_legacy_value.h`). The top 16 bits are the
   tag: `0xffff` object, `0xfffd` string, `0xfffb` bool/symbol,
   `0xfffa` undefined/null. Any other value is an IEEE double. The low 48 bits
   are the pointer.
3. **Typed arrays.** `JSTypedArrayBase::buffer_` points to a `JSArrayBuffer`,
   whose `data_` points to the raw bytes in the malloc heap. The array uses
   `length_` and `offset_` within that buffer. The object kind is
   `GCCell::kindAndSize_.kind_`, a `hermes::vm::CellKind`. Strings are
   `StringPrimitive`, with the length in `lengthAndFlags_` and the ASCII bytes
   after the header.

## Solve: break on `update`

[`update.gdb`](update.gdb):

```gdb
set debuginfod enabled off
set pagination off
break _24_update
commands
  silent
  set language c++
  # frame register = shr->stackPointer on entry; frame[-9] = 1st argument (NaN-boxed object)
  set $ta  = (hermes::vm::JSTypedArrayBase *)(((SHRuntime *)$rdi)->stackPointer[-9].raw & 0xffffffffffff)
  set $buf = (hermes::vm::JSArrayBuffer *)$ta->buffer_.raw
  printf "update(%u bytes): ", $ta->length_
  output/c *($buf->data_ + $ta->offset_)@$ta->length_
  echo \n
  continue
end
run
```

```
$ gdb -q -batch -x solve/update.gdb publish/main
update(8 bytes): {69 'E', 77 'M', 85 'U', 123 '{', 121 'y', 48 '0', 117 'u', 95 '_'}
update(9 bytes): {99 'c', 52 '4', 110 'n', 95 '_', 98 'b', 49 '1', 110 'n', 106 'j', 52 '4'}
update(8 bytes): {95 '_', 98 'b', 117 'u', 55 '7', 95 '_', 103 'g', 48 '0', 48 '0'}
update(16 bytes): {100 'd', 95 '_', 108 'l', 117 'u', 99 'c', 107 'k', 95 '_', 104 'h', 48 '0', 110 'n', 51 '3', 53 '5', 55 '7', 108 'l', 121 'y', 125 '}'}
Hash matched
```

Flag: `EMU{y0u_c4n_b1nj4_bu7_g00d_luck_h0n357ly}`.

Hypothetically, one could patch the `update` calls into `print` calls, but it is harder here than it would be in JS source.
The method name is a single string-table ID, shared by the class method definition and the call site.
`print` is a property of the global object, not of the hash instance, so a patch would have to rewrite the `get_by_id(obj, "update")` sequence in `_0_global` into a global lookup.
Reading the argument at a breakpoint is less work.

