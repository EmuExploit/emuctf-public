import hashlib
import os


def crc16(data: bytes) -> bytes:
    poly = 0x1021
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ poly) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc.to_bytes(2, "big")


def crc32(data: bytes) -> bytes:
    poly = 0xEDB88320
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
    crc ^= 0xFFFFFFFF
    return crc.to_bytes(4, "big")


def crc64(data: bytes) -> bytes:
    poly = 0x42F0E1EBA9EA3693
    crc = 0x0000000000000000
    for b in data:
        crc ^= b << 56
        for _ in range(8):
            if crc & 0x8000000000000000:
                crc = ((crc << 1) ^ poly) & 0xFFFFFFFFFFFFFFFF
            else:
                crc = (crc << 1) & 0xFFFFFFFFFFFFFFFF
    return crc.to_bytes(8, "big")


def md5(data: bytes) -> bytes:
    return hashlib.md5(data).digest()


def sha1(data: bytes) -> bytes:
    return hashlib.sha1(data).digest()


def sha224(data: bytes) -> bytes:
    return hashlib.sha224(data).digest()


def sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def sha384(data: bytes) -> bytes:
    return hashlib.sha384(data).digest()


def sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def sha3_224(data: bytes) -> bytes:
    return hashlib.sha3_224(data).digest()


def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def sha3_384(data: bytes) -> bytes:
    return hashlib.sha3_384(data).digest()


def sha3_512(data: bytes) -> bytes:
    return hashlib.sha3_512(data).digest()


def shake_128(data: bytes) -> bytes:
    return hashlib.shake_128(data).digest(32)


def shake_256(data: bytes) -> bytes:
    return hashlib.shake_256(data).digest(64)


def blake2b(data: bytes) -> bytes:
    return hashlib.blake2b(data).digest()


def blake2s(data: bytes) -> bytes:
    return hashlib.blake2s(data).digest()


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


def main():
    secret = os.urandom(16)
    secret_hash = hash_all(secret)

    print(f"Secret hash: {secret_hash.hex()}")
    data = input("Guess my secret>").encode()
    if hash_all(data) == secret_hash:
        print(":>")
        print(open("flag.txt", "r").read())
    else:
        print(":<")


if __name__ == "__main__":
    main()
