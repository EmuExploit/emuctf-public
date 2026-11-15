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
