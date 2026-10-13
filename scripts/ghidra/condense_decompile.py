"""Makes a cleaned decompile shorter to read: joins statements split over
several lines, drops variable declarations and null checks, and shortens
field access, method-table calls and object creation.

Usage: python -I condense_decompile.py <in.clean.c> <out.short.c> [name filter regex]

It is a reading aid only. Null checks are dropped but the field loads inside
them are kept as "//   v = x.field" lines. When something looks odd in the
output, go back to the .clean.c file.
"""
import re
import sys

KEYWORDS = ("return", "break", "continue", "goto", "else", "do")
DECLARATION = re.compile(r"^[A-Za-z_][\w ]*?[\s\*]+\w+(\s*\[\w+\])*;$")
LOAD = re.compile(r"(\w+) = (\(?\*?\w+\)?(?:\.\w+)+|\*\w+)(?=[,)]| ==)")


def statements(lines):
    """Join physical lines into statements (balanced brackets, proper ending)."""
    buffer, depth = [], 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("/*") and stripped.endswith("*/"):
            continue
        if not buffer:
            indent = len(line) - len(line.lstrip())
        buffer.append(stripped)
        depth += stripped.count("(") - stripped.count(")")
        if depth <= 0 and (stripped[-1] in ";{}:" or stripped in ("else", "do")):
            yield indent, " ".join(buffer)
            buffer, depth = [], 0
    if buffer:
        yield indent, " ".join(buffer)


def shorten(text):
    text = re.sub(r",?\s*\(MethodInfo \*\)0x0", "", text)
    text = re.sub(r"\(\*\(\(?(\w+)(?:->klass)?->vtable\)\._(\d+)_(\w+)\.methodPtr\)\s*\(", r"CALL \3#\2(", text)
    text = re.sub(r"\(\*\(?(\w+)->klass->vtable\[(\w+)\]\.methodPtr\)\s*\(", r"CALL slot[\2](", text)
    text = re.sub(r",?\s*\(?\(?\w+(?:->klass)?->vtable\)\.\s*_\d+_\w+\.\s*method\b", "", text)
    text = re.sub(r",?\s*\w+->klass->vtable\[\w+\]\.method\b", "", text)
    text = re.sub(r"thunk_FUN_1800f3b80\((\w+)_TypeInfo\)", r"new \1", text)
    text = re.sub(r"\((?:[A-Za-z_]\w*)(?: \w+)* ?\*+\)", "", text)          # pointer casts
    text = re.sub(r"\(\(?\*?(\w+)\)?->fields\)\.", r"\1.", text)
    text = re.sub(r"\b__(?:hx_)?this\b", "this", text)
    text = text.replace("play_day_border_", "").replace("play_day_", "")
    text = re.sub(r"\(\*?\(longlong \*\)\((\w+)_TypeInfo \+ 0xb8\)( \+ (\w+))?\)", r"STATIC(\1\2)", text)
    text = re.sub(r"\*\*\(\w+ \*\*\)\((\w+)_TypeInfo \+ 0xb8\)", r"STATIC(\1 + 0)", text)
    return re.sub(r"\s+", " ", text)


def condense(lines):
    items = list(statements(lines))
    null_labels = set()
    for index, (_, text) in enumerate(items):
        if re.match(r"^LAB_\w+:$", text) and index + 1 < len(items) and "FUN_1801271d0" in items[index + 1][1]:
            null_labels.add(text[:-1])
    out = []
    for indent, text in items:
        if text.startswith("FUN_1801271d0") or text.startswith("FUN_180126c20"):
            continue
        if text[:-1] in null_labels:
            continue
        word = re.match(r"\w+", text)
        if DECLARATION.match(text) and "=" not in text and "(" not in text and (not word or word.group(0) not in KEYWORDS):
            continue
        target = re.search(r"goto (LAB_\w+);$", text)
        if text.startswith("if (") and target and target.group(1) in null_labels and "0x0" in text:
            loads = ["%s = %s" % (m.group(1), m.group(2)) for m in LOAD.finditer(shorten(text))]
            if loads:
                out.append((indent, "//   " + "; ".join(loads)))
            continue
        out.append((indent, shorten(text)))
    return ["%s%s" % (" " * (indent // 2), text) for indent, text in out]


def main():
    lines = open(sys.argv[1], encoding="utf-8", errors="replace").read().split("\n")
    name_filter = re.compile(sys.argv[3]) if len(sys.argv) > 3 else None
    blocks, current = [], None
    for line in lines:
        if line.startswith("// ===== "):
            current = [line, []]
            blocks.append(current)
        elif current is not None:
            current[1].append(line)
    total_in = total_out = 0
    with open(sys.argv[2], "w", encoding="utf-8") as handle:
        for header, body in blocks:
            if name_filter and not name_filter.search(header):
                continue
            result = condense(body)
            total_in += len(body)
            total_out += len(result)
            handle.write(header + "\n" + "\n".join(result) + "\n\n")
    print("lines: %d -> %d" % (total_in, total_out))


if __name__ == "__main__":
    main()
