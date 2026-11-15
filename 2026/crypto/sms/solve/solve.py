from Crypto.Util.number import *
from pwn import *
from string import ascii_letters, digits
from tqdm import tqdm

MAX_BITS = 2048
MAX_LEN = MAX_BITS // 8

r = remote("localhost", 1337)


def set_username(username):
    r.recvuntil(b">>> ")
    r.sendline(b"1")
    r.sendline(username)

def get_bot_message():
    r.recvuntil(b">>> ")
    r.sendline(b"2")
    r.sendline(b"msg")

    r.recvuntil(b">>> ")
    r.sendline(b"3")
    r.recvuntil(b"You have ")
    num = int(r.recvline().split(b" messages")[0].decode())
    r.recvline()
    # print(f"num msgs {num = }")
    msgs = []
    for _ in range(num):
        l = r.recvline()
        # print(f"{l = }")
        msgs.append(list(map(int,l.strip().decode().split())))
    return msgs[-1]


ulen = MAX_LEN - 36
username = "a" * ulen
set_username(username)

c = None
enc = get_bot_message()
e = enc[1]
n = enc[2]

recovered_flag = ""
flag_charset = ascii_letters + digits + "_{}!@#$%^&*()-=+"
samples = 16
while True:
    found = False
    for guess_char in tqdm(flag_charset):
        ulen = MAX_LEN - 36 - len(recovered_flag) - 1
        username = "a" * ulen
        set_username(username)

        m = f"Do you want the flag, {username}? Here it is: {recovered_flag}{guess_char}"[:MAX_LEN].encode()
        # print(f"{m = }")
        assert len(m) == MAX_LEN
        m = bytes_to_long(m)
        expected_c = pow(m,e,n)

        ignore = []
        player_username = username
        other_m = [f"Hello {player_username}!",f"{player_username}, how are you doing?"]
        for _m in other_m:
            ignore.append(pow(bytes_to_long(_m.encode()),e,n))

        while True:
            enc = get_bot_message()
            c = enc[0]
            if c in ignore:
                continue
            
            if c == expected_c:
                found = True
                recovered_flag += guess_char
                print(f"found char: {guess_char = }")
            break
        if found:
            break
    print(f"{recovered_flag = }")
    if recovered_flag.endswith("}"):
        break










