#!/usr/bin/env python3
import base64
import codecs

a = base64.b32decode("IVGVK63DGRXDOXY=").decode()            # base32 (alphabet A-Z2-7 is in the string table)
b = bytes.fromhex("636875636b5f").decode()                  # plain hex
c = codecs.decode("guvf_vagb", "rot13")                     # ROT13 ([A-Za-z] regex, 13 and 26 constants)
d = bytes(x ^ 67 for x in bytes.fromhex("1c242b722731773e")).decode()  # hex, then XOR 67 (0x43)

print(a + b + c + d)
