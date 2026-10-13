"""Read the game's save folder: decrypt each store file and show what it holds.

How the game stores things (docs/save-format.md):

- Every entry of the "encrypted store" is one text file `<name>.sav` in the
  save folder. Its content is hexadecimal text: 8 hex digits per 32-bit word.
- The plain text is `PPSAVE1` + the value, padded with NUL characters to a
  multiple of 4 characters, 4 characters per word (first character in the
  highest byte), then encrypted as one XXTEA block. The key words are the MD5
  hex digest of a key string, split into four numbers. The key string is not
  stored in this repo: it is read from Il2CppDumper's stringliteral.json.
- Store names: `headers` (the tree of saves, an indented text), `save_<id>`
  (one save: the story facts as XML), `settings`, `stats`, `names`, `stash`.
- `platover.sav` is written without encryption.

Usage:
    python -I scripts/reference/savefile.py <save folder> \
        dumps/il2cppdumper/stringliteral.json [--dump <name>]

Without --dump it prints a summary of every file. With --dump it prints the
whole plain text of one entry (name without `.sav`).
"""

import hashlib
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

KEY_LITERAL_INDEX = 3240
PREFIX = "PPSAVE1"
DELTA = 0x9E3779B9
MASK = 0xFFFFFFFF
PLAIN_FILES = ("platover",)


def load_key(literals_path: str) -> str:
    with open(literals_path, encoding="utf-8") as f:
        return json.load(f)[KEY_LITERAL_INDEX]["value"]


def key_words(key: str) -> list[int]:
    digest = hashlib.md5(key.encode("utf-8")).hexdigest()
    return [int(digest[i:i + 8], 16) for i in range(0, 32, 8)]


def _mx(total: int, y: int, z: int, p: int, e: int, key: list[int]) -> int:
    return ((((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4))) ^
            ((total ^ y) + (key[(p & 3) ^ e] ^ z))) & MASK


def xxtea_encrypt(v: list[int], key: list[int]) -> list[int]:
    v = list(v)
    n = len(v)
    rounds = 6 + 52 // n
    total = 0
    z = v[n - 1]
    for _ in range(rounds):
        total = (total + DELTA) & MASK
        e = (total >> 2) & 3
        for p in range(n):
            y = v[p + 1] if p < n - 1 else v[0]
            z = v[p] = (v[p] + _mx(total, y, z, p, e, key)) & MASK
    return v


def xxtea_decrypt(v: list[int], key: list[int]) -> list[int]:
    v = list(v)
    n = len(v)
    rounds = 6 + 52 // n
    total = (rounds * DELTA) & MASK
    y = v[0]
    while total != 0:
        e = (total >> 2) & 3
        for p in range(n - 1, -1, -1):
            z = v[p - 1] if p > 0 else v[n - 1]
            y = v[p] = (v[p] - _mx(total, y, z, p, e, key)) & MASK
        total = (total - DELTA) & MASK
    return v


def encrypt_string(text: str, key: str) -> str:
    """app.XXTea.encryptString: text -> hex text."""
    while len(text) % 4 != 0:
        text += "\0"
    words = []
    for i in range(0, len(text), 4):
        a, b, c, d = (ord(ch) for ch in text[i:i + 4])
        # The game does not mask the characters: one above 255 spills into
        # its neighbours.
        words.append((d | ((((a << 8) | b) << 8 | c) << 8)) & MASK)
    out = xxtea_encrypt(words, key_words(key))
    return "".join(f"{w:08X}" for w in out)


def decrypt_string(hex_text: str, key: str) -> str:
    """app.XXTea.decryptString: hex text -> text (padding NULs are kept)."""
    if not hex_text:
        return ""
    words = [int(hex_text[i:i + 8], 16) for i in range(0, len(hex_text), 8)]
    out = xxtea_decrypt(words, key_words(key))
    chars = []
    for w in out:
        chars.extend(chr((w >> s) & 0xFF) for s in (24, 16, 8, 0))
    return "".join(chars)


def store_get(hex_text: str, key: str):
    """play.EncryptedStore.get: the value, or None when the prefix is wrong.

    The game returns the padding NULs with the value; so does this.
    """
    text = decrypt_string(hex_text, key)
    if not text.startswith(PREFIX):
        return None
    return text[len(PREFIX):]


def store_set(value: str, key: str) -> str:
    """play.EncryptedStore.set: the file content for a value."""
    return encrypt_string(PREFIX + value, key)


def parse_header(text: str) -> dict:
    """play.save.SaveHeader.fromString."""
    if text == "NEW":
        return {"id": "NEW", "parentId": "", "time": None, "day": 1,
                "money": 0, "family": 0}
    parts = text.split(";")
    return {"id": parts[0], "parentId": parts[1], "time": float(parts[2]),
            "day": int(parts[3]), "money": int(parts[4]),
            "family": int(parts[5])}


def parse_headers(text: str) -> list[dict]:
    """The `headers` entry: one header per line, one tab per tree level.

    Returns the lines in file order, each with its `depth`. (The game keeps
    only the first top-level line and what hangs under it.)
    """
    nodes = []
    for line in text.rstrip("\0").split("\n"):
        if not line.strip("\t\0 "):
            continue
        depth = len(line) - len(line.lstrip("\t"))
        node = parse_header(line.strip())
        node["depth"] = depth
        nodes.append(node)
    return nodes


def parse_facts(text: str) -> list[tuple[str, str]]:
    """A `save_<id>` entry: <facts><f p="path" v="text"/>...</facts>."""
    root = ET.fromstring(text.rstrip("\0"))
    return [(f.get("p"), f.get("v")) for f in root.iter("f")]


def parse_members(text: str) -> list[tuple[str, str]]:
    """`settings` and `stats`: <members><entry key= val=/>...</members>."""
    root = ET.fromstring(text.rstrip("\0"))
    return [(e.get("key"), e.get("val")) for e in root.iter("entry")]


def read_folder(folder: str, key: str) -> dict:
    """name -> plain text (None when the file does not decrypt)."""
    out = {}
    for file_name in sorted(os.listdir(folder)):
        if not file_name.endswith(".sav"):
            continue
        name = file_name[:-4]
        with open(os.path.join(folder, file_name), encoding="utf-8") as f:
            content = f.read()
        out[name] = content if name in PLAIN_FILES else store_get(content, key)
    return out


def format_time(ms) -> str:
    if ms is None:
        return "-"
    when = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return when.strftime("%Y-%m-%d %H:%M:%S UTC")


def main() -> None:
    folder, literals_path = sys.argv[1:3]
    key = load_key(literals_path)
    entries = read_folder(folder, key)

    if len(sys.argv) > 4 and sys.argv[3] == "--dump":
        text = entries.get(sys.argv[4])
        if text is None:
            print(f"no readable entry named {sys.argv[4]}")
            return
        print(text.rstrip("\0"))
        return

    print(f"{len(entries)} .sav files in {folder}")
    for name, text in entries.items():
        if text is None:
            print(f"\n[{name}] does not decrypt to the {PREFIX} prefix")
            continue
        print(f"\n[{name}] {len(text.rstrip(chr(0)))} characters")
        if name == "headers":
            for node in parse_headers(text):
                print("  " + "    " * node["depth"] +
                      f"{node['id']}  day {node['day']}  money {node['money']}"
                      f"  family {node['family']}  {format_time(node['time'])}")
        elif name.startswith("save_"):
            facts = parse_facts(text)
            print(f"  {len(facts)} facts")
            for path, value in facts:
                print(f"  {path} = {value}")
        elif name in ("settings", "stats"):
            for member, value in parse_members(text):
                print(f"  {member} = {value}")
        else:
            shown = text.rstrip("\0")
            print("  " + (shown if len(shown) <= 200 else shown[:200] + " ..."))


if __name__ == "__main__":
    main()
