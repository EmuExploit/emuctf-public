# rev/reversing

## Writeup

The binary reads in 13 bytes (plus one null byte) of user input, calls `sub_4011e9` on the input buffer, and then does a character-by-character comparison with some global string.

If the comparison succeeds, another global is XORed with the string to get the flag.

```c

00401280    int32_t main(int32_t argc, char** argv, char** envp)

0040128c        void* fsbase
0040128c        int64_t rax = *(fsbase + 0x28)
004012b4        setvbuf(fp: stdout, buf: nullptr, mode: 2, size: 0)
004012b9        int64_t buf = 0
004012c1        int32_t var_16 = 0
004012c8        int16_t var_12 = 0
004012dd        printf(format: "Enter the code: ")
004012f5        fgets(&buf, n: 0xe, fp: stdin)
00401301        sub_4011e9(&buf)
00401306        int32_t var_28 = 0
00401352        int32_t result
00401352
00401352        while (true)
00401352            if (var_28 u> 0xc)
0040135e                puts(str: "Correct!")
0040135e
004013ab                for (int32_t i = 0; i u<= 0xc; i += 1)
0040139e                    *(sx.q(i) + &data_404010) ^= (*data_404020)[sx.q(i)]
0040139e
004013c6                printf(format: "Flag: %s\n", &data_404010)
004013cb                result = 0
004013cb                break
004013cb
0040132d            if (*(&buf + sx.q(var_28)) != (*data_404020)[sx.q(var_28)])
00401339                puts(str: "Wrong code!")
0040133e                result = 1
00401343                break
00401343
00401348            var_28 += 1

```

The code for `sub_4011e9` is below:

```c
004011e9    void sub_4011e9(char* arg1)

00401209        if (arg1 == 0 || *arg1 == 0)
00401209            return
00401209
0040120b        uint32_t var_10_1 = 0
0040120b
00401279        for (int32_t i = strlen(arg1) - 1; var_10_1 s< i; i -= 1)
00401233            char rax_8 = arg1[sx.q(var_10_1)]
00401256            arg1[sx.q(var_10_1)] = arg1[sx.q(i)]
00401269            arg1[sx.q(i)] = rax_8
0040126b            var_10_1 += 1

```

It loops from the start, and the end of the string at the same time, swapping characters at each index. This ends up reversing the string in place.

To solve it, simply reverse the global string (AMWGCIQVWNELA), and enter it into the program as the input, so the comparison matches:

```bash
$ ./chal
Enter the code: ALENWVQICGWMA
Correct!
Flag: EMU{resrever}
```

## Alternative

You could also just XOR the global with the string yourself, and get the flag.
