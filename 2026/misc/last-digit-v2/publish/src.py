from Crypto.Util.number import *
from flag import flag
import sys
import json

sys.set_int_max_str_digits(0)

secret = getRandomNBitInteger(32)

for teddy in range(1337):
    try:
        inp = input("enter your number: ")
        your_number = json.loads(inp)["number"]
        n = secret * your_number
        print(f"last digit: {str(n)[-1]}")
    except:
        break

if int(input("enter secret: ")) == secret:
    print(flag)
