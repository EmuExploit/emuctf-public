# rev/easycrab

## Writeup

The decompilation is atroviously bad to read, but most of it is just reading in input, stripping whitespace, and converting to bytes.

The important part is this section:

```c

00416a11        do
00416939            char* rdx_9
00416939            rax_13, rdx_9 =
00416939                <core::iter::adapters::e...er::traits::iterator::Iterator>::next(&var_58)
0041696c            int64_t rax_15 = 1
0041696c
00416977            if (rdx_9 == 0)
00416977                rax_15 = 0
00416977
00416981            if ((rax_15 & 1) == 0)
004169b8                char* rax_17
004169b8                int64_t rdx_12
004169b8                rax_17, rdx_12 = <core::fmt::Arguments>::from_str(
004169b8                    "CORRECT!!!!\nWRONG!!!!\ncalled `Result::unwrap()` on an `Err` valueunsafe "
004169b8                "precondition(s) violated: hint::unreachable_unchecked must never be reached"
004169b8                "\nThis indicates a bug in the program. This Undefined Behavior check is "
004169b8                "optional, and cannot be relied on for safety.",
004169b8                    0xc)
004169da                int64_t* result = std::io::stdio::_print(rax_17, rdx_12)
004169e6                core::ptr::drop_glue::<alloc::string::String>(&var_a8, result)
004169f2                return result
004169f2
004169a1            i = <&u8 as core::ops::arith::Add<u8>>::add(rdx_9, rax_13.b)
004169a1
004169fc            if (rax_13 u>= 0x25)
00416a30                core::panicking::panic_bounds_check(rax_13, 0x25)
00416a30                noreturn
00416a11        while (i == (*"ENW~q8s7z")[rax_13])
```

This checks that the sum of each byte of the input, and its index equals some global called `ENC`:

```c
004089e0  char const easycrab::ENC[0x9] = "ENW~q8s7z"

004089e9                             82 69 7e 40 73 41 6e           .i~@sAn
004089f0  72 86 66 72 44 77 7c 6c 8b 5c 7b 8f 4d 8c 6c 7e  r.frDw|l.\{.M.l~
00408a00  86 55 53 6f a1 00 00 00 4e 6f 74 46 6f 75 6e 64  .USo....NotFound
```

Dump `ENC` from the binary, and subtract the index from each byte, and that will be the correct input and the flag:

```py
>>> enc = [0x45, 0x4e, 0x57, 0x7e, 0x71, 0x38, 0x73, 0x37, 0x7a, 0x82, 0x69, 0x7e, 0x40, 0x73, 0x41, 0x6e, 0x72, 0x86, 0x66, 0x72, 0x44, 0x77, 0x7c, 0x6c, 0x8b, 0x5c, 0x7b, 0x8f, 0x4d, 0\
x8c, 0x6c, 0x7e, 0x86, 0x55, 0x53, 0x6f, 0xa1]
>>> flag = [chr(enc[i] - i) for i in range(len(enc))]
>>> "".join(flag)
'EMU{m3m0ry_s4f3_buT_0bfUsCat1oN_f41L}'
>>>
```
