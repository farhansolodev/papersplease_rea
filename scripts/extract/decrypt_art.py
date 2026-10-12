"""Decrypt the game's Art.dat archive.

Art.dat is one XXTEA block covering the whole file. The key words are the MD5
hex digest of a key string, split into four 32-bit numbers. The key string is
not stored in this repo: it is read from Il2CppDumper's stringliteral.json.

Usage:
    python -I scripts/extract/decrypt_art.py extracted/Art.dat \
        dumps/il2cppdumper/stringliteral.json extracted/Art.dec
"""

import hashlib
import json
import struct
import sys

KEY_LITERAL_INDEX = 8555
DELTA = 0x9E3779B9
MASK = 0xFFFFFFFF


def key_words(key: str) -> list[int]:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return [int(digest[i:i + 8], 16) for i in range(0, 32, 8)]


def xxtea_decrypt(data: bytes, key: list[int]) -> bytes:
    n = len(data) // 4
    v = list(struct.unpack(f"<{n}I", data[:n * 4]))
    rounds = 6 + 52 // n
    total = (rounds * DELTA) & MASK
    y = v[0]
    while total != 0:
        e = (total >> 2) & 3
        for p in range(n - 1, -1, -1):
            z = v[p - 1] if p > 0 else v[n - 1]
            mx = ((((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4))) ^
                  ((total ^ y) + (key[(p & 3) ^ e] ^ z))) & MASK
            y = v[p] = (v[p] - mx) & MASK
        total = (total - DELTA) & MASK
    return struct.pack(f"<{n}I", *v) + data[n * 4:]


def main() -> None:
    art_path, literals_path, out_path = sys.argv[1:4]
    with open(literals_path, encoding="utf-8") as f:
        key = json.load(f)[KEY_LITERAL_INDEX]["value"]
    with open(art_path, "rb") as f:
        encrypted = f.read()

    decrypted = xxtea_decrypt(encrypted, key_words(key))
    with open(out_path, "wb") as f:
        f.write(decrypted)

    header_length = struct.unpack_from("<H", decrypted, 0)[0]
    print(f"decrypted {len(decrypted)} bytes -> {out_path}")
    print(f"header length field: {header_length}")
    print(f"header starts: {decrypted[2:122]!r}")


if __name__ == "__main__":
    main()
