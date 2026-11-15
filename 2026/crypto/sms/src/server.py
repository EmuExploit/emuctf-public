from Crypto.Util.number import *
from string import ascii_letters, digits
from flag import FLAG
import random

assert FLAG.startswith("EMU")
assert all(c in ascii_letters + digits + "_{}!@#$%^&*()-=+" for c in FLAG)

MAX_BITS = 2048

def rsa_keygen():
    p,q = [getPrime(MAX_BITS // 2) for _ in range(2)]
    n = p*q
    e = 0x10001
    d = pow(e, -1, (p-1)*(q-1))
    return (n,e,d)

def encrypt_message(rsa_key, message: bytes):
    n,e,d = rsa_key
    m = bytes_to_long(message[:MAX_BITS // 8])
    c = pow(m,e,n)
    return (c,e,n)

def get_bot_response():
    messages = [
        f"Hello {player_username}!",
        f"{player_username}, how are you doing?",
        f"Do you want the flag, {player_username}? Here it is: {FLAG}. Yeah, I'll just give it to you.",
    ]
    return random.choice(messages)

player_messages = []
bot_messages = []

allowed_username_chars = ascii_letters + "_" + digits

prompt = '''1) Set your username
2) Send a message
3) Check your messages
>>> '''

player_key = rsa_keygen()
player_username = "ctf_player"

bot_key = rsa_keygen()
bot_username = "just_a_bot"

print("ʕ•ᴥ•ʔ "*9)
print("ʕ•ᴥ•ʔ Welcome to SMS (Secure Messaging Service) ʕ•ᴥ•ʔ")
print("ʕ•ᴥ•ʔ Please choose an option                   ʕ•ᴥ•ʔ")
print("ʕ•ᴥ•ʔ "*9)

for i in range(0x10001):
    option = input(prompt)
    if option == "1":
        player_username = input("Enter new username: ")
        if any(c not in allowed_username_chars for c in player_username):
            print("invalid username :(")
            exit()

    elif option == "2":
        message = input("Enter message: ").encode()
        enc = encrypt_message(player_key, message)
        bot_messages.append(enc)

        bot_message = get_bot_response().encode()
        enc = encrypt_message(bot_key, bot_message)
        player_messages.append(enc)

        # purge old messages
        player_messages = player_messages[max(len(player_messages) - 10, 0):]

    elif option == "3":
        print(f"You have {len(player_messages)} messages!")

        print(f"{player_messages = }")

        [print(" ".join(map(str,list(msg)))) for msg in player_messages]

    else:
        print("ʕ•ᴥ•ʔ is sad :(")
        exit()

