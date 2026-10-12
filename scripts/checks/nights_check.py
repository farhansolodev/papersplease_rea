"""Checks of Nights.txt and scripts/reference/nights.py against the data files.

Usage: python -I nights_check.py <reference dir> <data dir> <stringliteral.json>
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import nights as N
import tabtree
import travspec as T

C = collections.Counter
data = sys.argv[2]
read = lambda name: open(os.path.join(data, name), encoding="utf-8", newline="").read()
code_strings = {entry["value"] for entry in json.load(open(sys.argv[3], encoding="utf-8"))}
problems = []

text = read("Nights.txt")
root = tabtree.parse(text)
lib = N.NightLib(text)
ids = [n.params[0] for n in root.nodes]
print("-- Nights.txt --")
print("  events:", len(ids), "| repeated ids:", [i for i, c in C(ids).items() if c > 1] or "none")
print("  id lines with more than one word:", [n.params for n in root.nodes if len(n.params) > 1] or "none")
signs = C()
for entry in root.nodes:
    for depth, node in tabtree.walk(entry):
        sign = node.params[0]
        signs[sign if sign in '"+-=?@>!^\\' else "(word) " + sign] += 1
print("  lines by first sign:", dict(signs))
for sign in signs:
    if sign in ("-", "!", "^", "\\") or sign.startswith("(word)"):
        problems.append("a line the night code does nothing with: " + sign)
quoted = [n.params for e in root.nodes for _, n in tabtree.walk(e) if any(" " in p for p in n.params)]
print("  lines with a quoted word containing a space:", quoted or "none")


def all_ops(ops):
    for op in ops:
        yield op
        yield from all_ops(op.ops)


every = [(event_id, op) for event_id, ops in lib.events.items() for op in all_ops(ops)]

print("\n-- scheduled events (+ lines) --")
plus = C((op.text.split(" ")[0], op.text.split(" ")[1]) for _, op in every if op.kind == N.ADD)
print("  days ahead used:", dict(sorted(C(d for d, _ in plus.elements()).items())))
for (days, target), _ in plus.items():
    if target not in lib.events:
        problems.append("scheduled event does not exist: " + target)
    if not days.isdigit():
        problems.append("days ahead is not a number: " + days)
print("  events that get scheduled:", sorted({t for _, t in plus}))

print("\n-- budget lines (> lines that are not YES / NO) --")
groups = [(e, op) for e, op in every if op.kind == N.GROUP and not op.text.startswith("?")]
budget = [(e, op) for e, op in groups if op.text not in ("YES", "NO")]
parts = C(len(T.split_and_trim(op.text, "|")) for _, op in budget)
third = C((T.split_and_trim(op.text, "|") + [None, None])[2] for _, op in budget)
print("  budget lines:", len(budget), "| by number of parts:", dict(parts), "| third part:", dict(third))
for _, op in budget:
    p = T.split_and_trim(op.text, "|")
    if len(p) < 2 or not re.fullmatch(r"-?\d+", p[1]):
        problems.append("budget line the code would reject or misread: " + op.text)
    for child in op.ops:
        if not (child.kind == N.GROUP and child.text in ("YES", "NO")):
            problems.append("a line under a budget line that is not YES or NO: " + child.text)
print("  with YES lines: %d | with NO lines: %d | with neither: %d" % (
    sum(any(c.text == "YES" for c in op.ops) for _, op in budget),
    sum(any(c.text == "NO" for c in op.ops) for _, op in budget),
    sum(not op.ops for _, op in budget)))
print("  positive amounts that are optional:", [op.text for _, op in budget
                                               if T.parse_int(T.split_and_trim(op.text, "|")[1]) > 0
                                               and len(T.split_and_trim(op.text, "|")) > 2])
stray = [(e, op.text) for e, op in groups if op.text in ("YES", "NO")
         and not any(op in b.ops for _, b in budget)]
print("  YES / NO groups not directly under a budget line:", stray or "none")

print("\n-- commands (@ lines) --")
commands = C(op.text.split(" ")[0] for _, op in every if op.kind == N.COMMAND)
print("  ", dict(commands))
handled_exact = {"MakeSonSad", "MakeSonHappy", "AdoptNiece", "RemoveSavings", "TakeFamilyPassports"} | \
    {"Upgrade-" + u for u in N.UPGRADES}
prefixes = ("GivePaper", "TakePaper", "End", "Include", "Achievement", "Escape")
for name in commands:
    if name not in handled_exact and not name.startswith(prefixes) and name != "RenameSleepButton":
        problems.append("command the night code does not know: " + name)
ends = set(re.findall(r'<end\s+id="([^"]+)"', read("Ends.xml"))) or set(re.findall(r'id="([^"]+)"', read("Ends.xml")))
papers_xml = read("Papers.xml")
for _, op in every:
    if op.kind != N.COMMAND:
        continue
    word, _, rest = op.text.partition(" ")
    if word == "Include" and rest not in lib.events:
        problems.append("Include of an event that does not exist: " + rest)
    if word == "End" and rest not in ends:
        problems.append("End id not in Ends.xml: " + rest)
    if word in ("GivePaper", "TakePaper") and ('id="%s"' % rest) not in papers_xml:
        problems.append("paper not in Papers.xml: " + rest)
    if word == "RenameSleepButton":
        print("  RenameSleepButton text id %r is a text entry: %s" % (rest, ('id="%s"' % rest) in read("Text.xml")))
print("  End ids used:", sorted({op.text.split(" ")[1] for _, op in every if op.kind == N.COMMAND and op.text.startswith("End ")}))
print("  papers given / taken:", sorted({op.text for _, op in every if op.kind == N.COMMAND and op.text.split(" ")[0] in ("GivePaper", "TakePaper")}))

print("\n-- conditions and facts --")
operators, lhs = C(), C()
for _, op in every:
    if op.kind == N.GROUP and op.text.startswith("?"):
        tokens = tabtree.split_quoted(op.text[1:])
        if len(tokens) % 4 != 3:
            problems.append("condition with an unexpected number of words: " + op.text)
        for i in range(0, len(tokens), 4):
            lhs[tokens[i]] += 1
            operators[tokens[i + 1]] += 1
        for glue in tokens[3::4]:
            if glue not in ("&&", "||"):
                problems.append("condition glue that is neither && nor ||: " + glue)
print("  operators:", dict(operators))
set_paths = C(op.text for _, op in every if op.kind == N.SET)
print("  facts tested:", dict(lhs))
print("  facts set:", dict(set_paths))
for op_name in operators:
    if op_name not in ("==", "!=", "has", "!has", "<", "<=", ">", ">="):
        problems.append("operator the tester does not know: " + op_name)
names = sorted(set(lhs) | set(set_paths))
print("  of these, named in the code's strings:", [n for n in names if n in code_strings])
print("  only in data files:", [n for n in names if n not in code_strings])

print("\n-- who names each event --")
table, _, _ = T.load(data)
from_days = C(i for c in table.col_ids[1:] for i in T.split_and_trim(table.cell(c, "NIGHTEVENTS"), "\n"))
travelers = tabtree.strip_block_comments(read("Travelers.txt"))
from_travelers = C(m.group(1) for m in re.finditer(r"^\s*@\s+Night\s+(\S+)", travelers, re.M))
from_plus = {t for _, t in plus}
from_include = {op.text.split(" ")[1] for _, op in every if op.kind == N.COMMAND and op.text.startswith("Include ")}
from_code = {i for i in ids if i in code_strings}
for name in list(from_days) + list(from_travelers):
    if name not in lib.events:
        problems.append("night event named elsewhere but missing: " + name)
print("  Days.csv: %d | Travelers.txt `Night`: %s | scheduled: %d | included: %d | whole word in the code's strings: %s" % (
    len(from_days), sorted(from_travelers), len(from_plus), len(from_include), sorted(from_code)))
unnamed = [i for i in ids if i not in from_days and i not in from_travelers and i not in from_plus
           and i not in from_include and i not in from_code]
print("  events nothing names:", unnamed or "none")

print("\n-- behaviour of the reference --")
night = N.Night(lib, {"Night/Savings": "50", "Night/Apartment": "C8", "Night/ApartmentTimer": "1"}, 12)
night.apply_event_with_id("APARTMENT_UPGRADE")
print("  APARTMENT_UPGRADE with savings 50, class 8, timer 1:", night.messages,
      [(l.name, l.cost, l.must_pay) for l in night.budget.lines], "| scheduled", night.calendar.to_string())
line = night.budget.lines[0]
line.enabled = True
night.apply_yes_no()
print("    after ticking the line:", {k: v for k, v in night.facts.items() if k != "Night/Savings"})
if night.facts.get("Night/Apartment") != "C7" or night.facts.get("Night/Rent") != "-30":
    problems.append("moving to class 7 did not set the apartment and rent")
for count, expect in ((0, 0), (3, 5), (5, 10), (13, 30)):
    night = N.Night(lib, {"Game/NumDetains": str(count)}, 20)
    night.apply_event_with_id("DETAIN_PAYOUT")
    got = night.budget.lines[0].cost if night.budget.lines else 0
    print("  DETAIN_PAYOUT with %2d detains: bonus %d, detains left %s" % (count, got, night.facts["Game/NumDetains"]))
    if got != expect:
        problems.append("detain bonus for %d detains" % count)
night = N.Night(lib, {"Night/NumEscapePassports": "3", "Night/HaveNiece": "1"}, 30,
                alive=["wife", "son", "uncle", "mil", "niece"])
night.apply_event_with_id("ESCAPE")
print("  ESCAPE with 3 passports:", night.messages, [(l.name, l.cost) for l in night.budget.lines])
night.budget.lines[0].enabled = True
print("    sleep button text id when ticked:", night.budget.lines[0].rename_sleep_button)
night.apply_yes_no()
print("    taken, left behind:", night.escape, "| ending:", night.want_end_id,
      "|", {k: v for k, v in night.facts.items() if k.startswith("End/")})
if night.escape != (["son", "wife"], ["niece", "uncle", "mil"]) or night.want_end_id != "flee":
    problems.append("escape with 3 passports")
night = N.Night(lib, {"Game/HelpedEzic": "YES", "Night/AttackResult": "SOLVED"}, 31)
night.apply_event_with_id("FINAL")
print("  FINAL after helping Ezic and stopping the attack, wall safe:", night.want_end_id)
night.apply_op(N.Op(N.COMMAND, "End something-else"))
print("    a second End command changes it:", night.want_end_id != "help-ezic-kill-attackers-wall-safe")
calendar = N.Calendar(lib, "13:EZIC_TAKESAVINGS;15:EZIC_CLEARED;oops;13:NIECE")
print("  calendar read back:", calendar.to_string(), "| night 13:", calendar.get_events(13))
budget = N.Budget()
for name, cost, kind in (("rent", -25, N.MUST_PAY), ("salary", 30, N.MUST_PAY), ("food", -20, N.OPTIONAL_YES),
                         ("gift", 100, N.OPTIONAL_YES), ("fine", -20, N.MUST_PAY), ("heat", -10, N.OPTIONAL_YES)):
    budget.add_line(name, cost, kind)
print("  budget order after adding rent, salary, food, gift, fine, heat:", [l.name for l in budget.lines])
costs = [l.cost > 0 for l in budget.lines]
if costs != sorted(costs, reverse=True):
    problems.append("income lines are not before cost lines")

print("\nproblems:", sorted(set(problems)) or "none")
