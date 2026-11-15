# crypto/delphi

## Writeup

The challenge source is very simple, allowing the player to either encrypt the flag, or encrypt their own message:

```py
from Crypto.Cipher import ARC4
import os


def encrypt(key, message):
    cipher = ARC4.new(key)
    return cipher.encrypt(message)


def main():
    key = os.urandom(16)
    flag = open("flag.txt", "r").read()

    while True:
        print("~= QUERY THE ORACLE OF DELPHI! =~")
        print("1) Get encrypted flag")
        print("2) Encrypt your own message")
        print("3) Exit")
        choice = int(input("> "))

        if choice == 1:
            print("Encrypted flag:", encrypt(key, flag.encode()).hex())

        elif choice == 2:
            print("Enter your message (hex)")
            msg = bytes.fromhex(input("> "))
            print("Encrypted message:", encrypt(key, msg).hex())

        elif choice == 3:
            print("The oracle wishes you a blessed day")
            return

        else:
            print("The oracle cannot decipher your query!")


if __name__ == "__main__":
    main()
```

Importantly, it reinitialises the cipher RC4 with the same key every time, so each encryption generates the same keystream.

RC4 is a stream cipher, meaning it will generate a "keystream" and then XOR the keystream bytes with the plaintext to get the ciphertext.

This also means that encryption is the same process as decryption.

To solve the challenge, we can get the encrypted flag, and then pass it to the "encrypt" function which will decrypt it. Decoding it from hex will then return the flag:

```bash
$ nc localhost 10000
~= QUERY THE ORACLE OF DELPHI! =~
1) Get encrypted flag
2) Encrypt your own message
3) Exit
> 1
Encrypted flag: e22f6e402a2cfa12c55d7e345772bcfbd6d73c44770a854adce1d2deab4e1b6409ecd820b82ea9ad7734e813e129570de22d111f
~= QUERY THE ORACLE OF DELPHI! =~
1) Get encrypted flag
2) Encrypt your own message
3) Exit
> 2
Enter your message (hex)
> e22f6e402a2cfa12c55d7e345772bcfbd6d73c44770a854adce1d2deab4e1b6409ecd820b82ea9ad7734e813e129570de22d111f
Encrypted message: 454d557b7468655f6f7261636c655f73686f756c645f7265746972655f74686569725f73747265616d5f63697068657273217d0a
~= QUERY THE ORACLE OF DELPHI! =~
1) Get encrypted flag
2) Encrypt your own message
3) Exit
>

$ echo 454d557b7468655f6f7261636c655f73686f756c645f7265746972655f74686569725f73747265616d5f63697068657273217d0a | xxd -r -p
EMU{the_oracle_should_retire_their_stream_ciphers!}
```
