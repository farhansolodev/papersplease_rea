"""Cross-check of docs/responses-and-events.md against Travelers.txt and the code's strings.

Usage: python -I responses_check.py <reference dir> Travelers.txt stringliteral.json
"""
import sys, json, collections

sys.path.insert(0, sys.argv[1])
import tabtree

C = collections.Counter
root = tabtree.parse(open(sys.argv[2], encoding="utf-8", newline="").read())
code = {l["value"] for l in json.load(open(sys.argv[3], encoding="utf-8"))}

events = C()
buttons = C()
button_lines = C()
for entry in root.nodes:
    for _, n in tabtree.walk(entry):
        p = n.params or []
        if p and p[0] == ">" and len(p) > 1:
            events[" ".join(p[1:])] += 1
        if p and p[0] == "@":
            buttons[p[1] if len(p) > 1 else ""] += 1
            button_lines[" ".join(p[1:])] += 1

print("-- response names used in Travelers.txt (> lines) --")
called = {e: e in code for e in events}
print("  distinct:", len(events))
print("  also a string in the code:", sorted(e for e, c in called.items() if c))
print("  not a code string:", sorted(e for e, c in called.items() if not c))

known_exact = {"Fingerprint", "Detain", "Search", "Leave", "Leave Left", "Leave Right", "Resist",
               "Unresist", "Break"}
known_prefix = ("Custom", "News", "Want", "Reject", "NoFiler", "Night", "Tomorrow", "End", "Leave")
print("\n-- @ button lines --")
print("  by first word:", dict(buttons.most_common()))
unknown = [b for b in button_lines if b not in known_exact and not b.startswith(known_prefix)]
print("  lines the engine does nothing with:", unknown)
print("  Leave variants:", {b: c for b, c in button_lines.items() if b.startswith("Leave")})

print("\n-- DEFAULT entry --")
default = next(e for e in root.nodes if e.params[0] == "DEFAULT")
def show(node, depth):
    for ch in node.nodes:
        p = ch.params
        if p[0] in (">", "?", "BREAK"):
            print("  " + "  " * depth + " ".join(p) + (f"   ({len(ch.nodes)} lines)" if p[0] == ">" else ""))
            if p[0] == "?":
                show(ch, depth + 1)
        else:
            print("  " + "  " * depth + "(ignored: " + " ".join(p)[:40] + ")")
show(default, 0)
