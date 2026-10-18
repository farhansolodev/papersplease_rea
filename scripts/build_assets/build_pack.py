"""Builds the start pack: one file holding the game files the browser build
loads at the start (docs/DESIGN.md, "Loading and caching"; milestone 1a).

    python -I scripts/build_assets/build_pack.py [out file]

The default output is build/assets/start.pack (gitignored: it holds game
assets, CLAUDE.md rule 1). scripts/build_web.py calls build() and gives the
pack a fingerprinted name.

Pack format (all numbers little-endian), read by port/core/src/pack.rs:

    "PPK1"                      4 bytes
    count                       u32
    count x entry:  name length u16, name (UTF-8), offset u32, size u32
    the files' bytes, one after another; an offset counts from the start of
    this data area

Milestone 1a puts in: the twelve font files and their sheets (PNG kept as
PNG; the core decodes them), data/Fonts.xml, and strings.json with the one
text the font code needs, wrap_hyphen. Milestone 1b adds the title screen's
pictures as pictures/<file name> (PICTURES) and its three texts to
strings.json (STRINGS). The English language pack is NOT
applied here: of the 23 texts it changes none is in Text.xml, so Text.xml
strings are the same with or without it (docs/milestone-1.md). Files it does
change (Travelers.txt, Facts.xml, Endlesses.xml) need it applied
(scripts/reference/locpack.py) when they go into a pack.
"""

import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS = os.path.join(ROOT, "extracted", "art", "assets")
DEFAULT_OUT = os.path.join(ROOT, "build", "assets", "start.pack")
PICTURES = ["Title.png", "PushButton.png", "SettingsButton.png"]
STRINGS = ["wrap_hyphen", "menu_story", "menu_endless", "created_by"]


def text_item(text_xml, item_id):
    """The text of one <item id="..."><t>...</t></item> in Text.xml."""
    root = ET.fromstring(text_xml)
    for item in root.iter("item"):
        if item.get("id") == item_id:
            return item.find("t").text or ""
    raise KeyError(item_id)


def files():
    """(name in the pack, bytes) in a fixed order."""
    out = []
    fonts_xml = open(os.path.join(ASSETS, "data", "Fonts.xml"), "rb").read()
    out.append(("data/Fonts.xml", fonts_xml))
    names = sorted(set(ET.fromstring(fonts_xml.decode("utf-8")).iter("font")), key=lambda n: n.get("file"))
    for node in names:
        base = node.get("file")
        fnt = open(os.path.join(ASSETS, "fonts", base + ".fnt"), "rb").read()
        out.append(("fonts/" + base + ".fnt", fnt))
        for page in re.findall(rb'<page [^>]*file="([^"]+)"', fnt):
            out.append(("fonts/" + page.decode(), open(os.path.join(ASSETS, "fonts", page.decode()), "rb").read()))
    seen, unique = set(), []
    for name, data in out:                      # a file shared by two ids is stored once
        if name not in seen:
            seen.add(name)
            unique.append((name, data))
    for name in PICTURES:
        unique.append(("pictures/" + name, open(os.path.join(ASSETS, name), "rb").read()))
    text_xml = open(os.path.join(ASSETS, "data", "Text.xml"), encoding="utf-8").read()
    strings = {key: text_item(text_xml, key) for key in STRINGS}
    unique.append(("strings.json", json.dumps(strings, ensure_ascii=False).encode("utf-8")))
    return unique


def build():
    entries = files()
    head = b"PPK1" + struct.pack("<I", len(entries))
    table, data, offset = b"", b"", 0
    for name, blob in entries:
        raw = name.encode("utf-8")
        table += struct.pack("<H", len(raw)) + raw + struct.pack("<II", offset, len(blob))
        data += blob
        offset += len(blob)
    return head + table + data


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUT
    os.makedirs(os.path.dirname(out), exist_ok=True)
    blob = build()
    with open(out, "wb") as f:
        f.write(blob)
    print(f"{len(files())} files, {len(blob):,} bytes -> {out}")


if __name__ == "__main__":
    main()
