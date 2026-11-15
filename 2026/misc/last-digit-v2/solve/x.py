import json
from pwn import *
from string import digits
import sys

r = remote("localhost", 1337)

def oracle(num):
    json_data = {
        "number":float(num)
    }
    r.recvuntil(b"your number: ")
    r.sendline(json.dumps(json_data))
    l = r.recvline()
    return l.split(b"digit: ")[-1].strip().decode()

lo = 10**298
hi = 10**300

for trial in range(1000):
    middle = (lo + hi) // 2
    ret = oracle(middle)
    if ret in digits:
        # too low
        print("too low")
        lo = middle
    else:
        # too high
        print("too high")
        hi = middle
    print(f"{middle = } {ret = }")
    if abs(lo - hi) <= 1:
        print(f"breaking {trial = }")
        break


float_max = sys.float_info.max
print(f"{float_max / lo = }")

ans = round(float_max / lo)
r.sendline(str(ans))
r.sendline(str(ans))

r.interactive()