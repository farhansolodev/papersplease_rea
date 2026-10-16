"""Decode the Layout object printed by scripts/ghidra/EmulateLayout.java.

Usage:
    python -I layout_dump.py <emulator log> <dump.cs> [stringliteral.json]

Prints every field of the desktop Layout with its value: rectangles as
x, y, w, h; points as x, y; numbers; enum values by name; the dock points
(key -> entry, home, clamp, clip). Field offsets and types come from
Il2CppDumper's dump.cs, so nothing is typed in by hand.
"""

import json
import re
import struct
import sys


def parse_log(path):
    text = open(path, encoding="utf-8", errors="replace").read()
    # Ghidra wraps long lines; join the pieces of each "INFO  EmulateLayout.java>" line.
    text = re.sub(r"\s*\(GhidraScript\)\s*\n", "\n", text)
    text = re.sub(r"\n(?!INFO|WARN|ERROR)", " ", text)
    objects = {}
    layout = None
    dock_sets = []
    for line in text.splitlines():
        line = re.sub(r"^INFO\s+EmulateLayout\.java>\s*", "", line)
        if line.startswith("LAYOUT_OBJECT "):
            layout = int(line.split()[1], 16)
        elif line.startswith("OBJ "):
            parts = line.split()
            addr = int(parts[1], 16)
            cls = parts[2]
            words = [int(w, 16) for w in parts[3:]]
            objects[addr] = (cls, words)
        elif line.startswith("VCALL haxe.ds.StringMap_TypeInfo slot 36"):
            m = re.search(r"rdx (\S+) r8 (\S+)", line)
            dock_sets.append((m.group(1), int(m.group(2), 16)))
    return layout, objects, dock_sets


def parse_fields(dump_path, class_name):
    """Instance fields of one class: list of (name, type, offset)."""
    lines = open(dump_path, encoding="utf-8").read().splitlines()
    start = None
    for i, line in enumerate(lines):
        if line.startswith("public class %s : " % class_name):
            start = i
            break
    fields = []
    for line in lines[start + 1:]:
        if line.strip().startswith("// Methods"):
            break
        m = re.match(r"\s*public (\S+) (\w+); // 0x([0-9A-F]+)", line)
        if m and " static " not in line:
            fields.append((m.group(2), m.group(1), int(m.group(3), 16)))
    return fields


def enum_names(dump_path, enum_name):
    lines = open(dump_path, encoding="utf-8").read().splitlines()
    names = []
    inside = False
    for line in lines:
        if line.startswith("public class %s : Enum" % enum_name):
            inside = True
            continue
        if inside:
            m = re.match(r"\s*public static readonly %s (\w+);" % enum_name, line)
            if m:
                names.append(m.group(1))
            elif "// Methods" in line:
                break
    return names


def as_double(word):
    return struct.unpack("<d", struct.pack("<Q", word))[0]


def word_at(objects, addr, offset):
    """The 8-byte word at addr + offset (offset >= 0x10)."""
    cls, words = objects[addr]
    return words[(offset - 0x10) // 8]


def fmt(v):
    return ("%d" % v) if float(v).is_integer() else repr(v)


def main():
    log, dump_cs = sys.argv[1], sys.argv[2]
    literals = None
    if len(sys.argv) > 3:
        literals = json.load(open(sys.argv[3], encoding="utf-8"))
    layout, objects, dock_sets = parse_log(log)
    fields = parse_fields(dump_cs, "Layout")

    def rect(addr):
        if addr == 0:
            return None
        return tuple(as_double(word_at(objects, addr, 0x10 + 8 * k)) for k in range(4))

    def point(addr):
        if addr == 0:
            return None
        return tuple(as_double(word_at(objects, addr, 0x10 + 8 * k)) for k in range(2))

    def enum_value(addr, type_name):
        if addr == 0:
            return None
        index = word_at(objects, addr, 0x10) & 0xFFFFFFFF
        names = enum_names(dump_cs, type_name)
        return names[index] if index < len(names) else "#%d" % index

    out = {}
    for name, typ, off in fields:
        raw = word_at(objects, layout, off & ~7)
        shift = (off & 7) * 8
        if typ == "Rect":
            v = rect(raw)
            text = "none" if v is None else "x %s, y %s, w %s, h %s" % tuple(fmt(c) for c in v)
        elif typ == "PointData":
            v = point(raw)
            text = "none" if v is None else "(%s, %s)" % tuple(fmt(c) for c in v)
        elif typ == "double":
            v = as_double(raw)
            text = fmt(v)
        elif typ == "int":
            v = (raw >> shift) & 0xFFFFFFFF
            if v >= 1 << 31:
                v -= 1 << 32
            text = str(v)
        elif typ == "bool":
            v = bool((raw >> shift) & 0xFF)
            text = str(v).lower()
        elif typ in ("Shape", "Aspect", "BoothLayout", "ConsoleKind"):
            v = enum_value(raw, typ)
            text = str(v)
        elif typ == "StringMap":
            v = "dockPoints" if raw else None
            text = "see below" if raw else "none"
        else:
            v = hex(raw)
            text = "(object %s)" % hex(raw) if raw else "none"
        out[name] = v
        print("%-36s %-11s %s" % (name, typ, text))

    print()
    print("dock points (StringMap.set calls, in order):")
    entries = enum_names(dump_cs, "DockPointEntry")
    docks = {}
    for key, dp in dock_sets:
        idx = int(key.split("_")[1])
        key_text = literals[idx]["value"] if literals else key
        entry = enum_value(word_at(objects, dp, 0x10), "DockPointEntry") if word_at(objects, dp, 0x10) else None
        home = rect(word_at(objects, dp, 0x18))
        clip = rect(word_at(objects, dp, 0x20))
        clamp = rect(word_at(objects, dp, 0x28))
        docks[key_text] = {"entry": entry, "home": home, "clamp": clamp, "clip": clip}
        print("  %-10s entry %s" % (key_text, entry))
        for label, r in (("home", home), ("clamp", clamp), ("clip", clip)):
            print("             %-5s %s" % (label, "none" if r is None else
                                             "x %s, y %s, w %s, h %s" % tuple(fmt(c) for c in r)))
    out["dockPoints"] = docks
    if len(sys.argv) > 4:
        json.dump(out, open(sys.argv[4], "w"), indent=1)


if __name__ == "__main__":
    main()
