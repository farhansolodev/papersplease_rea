"""Unpack a decrypted Art.dat (see decrypt_art.py) into individual files.

Layout of the decrypted archive:
    u16 little-endian   length of the table of contents in bytes
    table of contents   Haxe-serialized array of {name, size} objects
    file data           the files back to back, in table order

Usage:
    python -I scripts/extract/unpack_art.py extracted/Art.dec extracted/art
"""

import os
import struct
import sys
from urllib.parse import unquote


class HaxeReader:
    """Reads the subset of Haxe's serialization format the table uses."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.strings: list[str] = []

    def _digits(self) -> int:
        start = self.pos
        while self.text[self.pos] in "-0123456789":
            self.pos += 1
        return int(self.text[start:self.pos])

    def value(self):
        tag = self.text[self.pos]
        self.pos += 1
        if tag == "a":  # array, ends with h
            items = []
            while self.text[self.pos] != "h":
                items.append(self.value())
            self.pos += 1
            return items
        if tag == "o":  # object, key/value pairs, ends with g
            fields = {}
            while self.text[self.pos] != "g":
                key = self.value()
                fields[key] = self.value()
            self.pos += 1
            return fields
        if tag == "y":  # url-encoded string: y<length>:<text>
            length = self._digits()
            self.pos += 1
            text = unquote(self.text[self.pos:self.pos + length])
            self.pos += length
            self.strings.append(text)
            return text
        if tag == "R":  # reference to an earlier string
            return self.strings[self._digits()]
        if tag == "i":
            return self._digits()
        if tag == "z":
            return 0
        if tag == "n":
            return None
        raise ValueError(f"unsupported tag {tag!r} at {self.pos - 1}")


def main() -> None:
    archive_path, out_dir = sys.argv[1:3]
    with open(archive_path, "rb") as f:
        data = f.read()

    toc_length = struct.unpack_from("<H", data, 0)[0]
    reader = HaxeReader(data[2:2 + toc_length].decode("utf-8"))
    entries = reader.value()
    if reader.pos != len(reader.text):
        raise ValueError("table of contents has trailing data")

    out_root = os.path.abspath(out_dir)
    offset = 2 + toc_length
    written = 0
    by_extension: dict[str, list[int]] = {}
    for entry in entries:
        name, size = entry["name"], entry["size"]
        if size <= 0:
            continue
        target = os.path.abspath(os.path.join(out_root, name))
        if not target.startswith(out_root + os.sep):
            raise ValueError(f"unsafe path in archive: {name!r}")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "wb") as f:
            f.write(data[offset:offset + size])
        offset += size
        written += 1
        stats = by_extension.setdefault(os.path.splitext(name)[1].lower(), [0, 0])
        stats[0] += 1
        stats[1] += size

    print(f"entries: {len(entries)}, files written: {written}")
    print(f"bytes used: {offset} of {len(data)} (unused tail: {len(data) - offset})")
    for extension, (count, size) in sorted(by_extension.items()):
        print(f"  {extension or '(none)':8} {count:5} files {size:10} bytes")


if __name__ == "__main__":
    main()
