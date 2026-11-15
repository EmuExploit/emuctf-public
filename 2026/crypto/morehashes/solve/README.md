# crypto/morehashes

## Writeup

The challenge asks you to find a preimage of a hash comprised of several hashes/checksums of some secret.

The hash functions are:

```py
funcs = [
    md5,
    sha1,
    sha224,
    sha256,
    sha384,
    crc16,
    crc32,
    crc64,
    sha512,
    sha3_224,
    sha3_256,
    sha3_384,
    sha3_512,
    shake_128,
    shake_256,
    blake2b,
    blake2s,
]

def hash_all(data: bytes) -> bytes:
    for f in funcs:
        data = f(data)

    return data
```

`crc16` has an output space of 2 bytes, which reduces the entire hash output space to 2 bytes of entropy. This makes it very fast to bruteforce. To avoid issues with python `input()` and non-printable characters, the example solver bruteforces combinations of 4 ascii letters until the flag is received. This is usually in under 5 seconds.
