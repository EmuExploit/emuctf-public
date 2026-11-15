from pwn import *
from string import ascii_letters
from itertools import product
from tqdm import tqdm
from src import hash_all

p = remote("localhost", 10000)
p.recvuntil(b"Secret hash: ")
hash = p.recvline().decode()

for chars in tqdm(product(ascii_letters, repeat=4)):
    s = "".join(chars).encode()
    if hash_all(s) == bytes.fromhex(hash):
        p.sendline(s)
        p.recvuntil(b":>\n")
        flag = p.recvline()
        print(flag)
        exit()

print("Failed")
