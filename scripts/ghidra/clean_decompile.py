"""Make Ghidra's decompile of IL2CPP code easier to read.

Removes four kinds of runtime boilerplate that carry no game logic, and shows
string constants as their text instead of StringLiteral_N:

  1. the one-time metadata setup block at the top of each function
  2. "has this class been initialised yet" checks
  3. null checks whose only body is the null-reference error call
  4. garbage-collector write-barrier calls after a field is stored

Each pattern only matches its exact shape, so real logic is left alone. The
count of removals is printed so a surprising number can be noticed.

Usage:
    python -I scripts/ghidra/clean_decompile.py decompiled/in.c \
        dumps/il2cppdumper/stringliteral.json decompiled/out.c
"""

import json
import re
import sys

NULL_ERROR = r"FUN_1801271d0\(\);"

PATTERNS = [
    ("metadata setup", re.compile(
        r"[ \t]*if \(DAT_\w+ == '\\0'\) \{\n"
        r"(?:[ \t]*thunk_FUN_1800eeee0\([^;]*\);\n)+"
        r"[ \t]*DAT_\w+ = '\\x01';\n"
        r"[ \t]*\}\n")),
    ("class init check", re.compile(
        r"[ \t]*if \(\(\(\*\(byte \*\)\((\w+) \+ 0x133\) & 4\) != 0\)\s*&&\s*"
        r"\(\*\(int \*\)\(\1 \+ 0xe0\) == 0\)\) \{\s*"
        r"il2cpp_runtime_class_init\([^;]*\);\s*\}\n")),
    ("null check", re.compile(
        r"[ \t]*if \([^{};\n]* == \([^()]*\)0x0\) \{\n"
        r"[ \t]*/\* WARNING: Subroutine does not return \*/\n"
        r"[ \t]*" + NULL_ERROR + r"\n"
        r"[ \t]*\}\n")),
    ("write barrier", re.compile(r"[ \t]*thunk_FUN_180125b00\([^;]*\);\n")),
]


def main() -> None:
    in_path, literals_path, out_path = sys.argv[1:4]
    with open(in_path, encoding="utf-8") as f:
        text = f.read()
    with open(literals_path, encoding="utf-8") as f:
        literals = json.load(f)

    before = text.count("\n")
    for name, pattern in PATTERNS:
        text, count = pattern.subn("", text)
        print(f"removed {count:5} x {name}")

    def literal(match: re.Match) -> str:
        return json.dumps(literals[int(match.group(1))]["value"], ensure_ascii=False)

    text, count = re.subn(r"StringLiteral_(\d+)", literal, text)
    print(f"replaced {count} string constants")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"lines: {before} -> {text.count(chr(10))}")


if __name__ == "__main__":
    main()
