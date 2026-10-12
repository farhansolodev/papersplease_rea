"""Reference implementation of night events: data.NightLib, data.NightEvent,
play.night.Calendar, and the parts of play.night.Family and
play.night.Budget that run an event's lines (docs/nights-txt-format.md).

Not covered here: the family members' health, the standard budget lines
(salary, rent, food, heat, medicine) and balancing the budget. Those belong
to the Family constructor and applyBudget, which are not studied yet. A
caller supplies who is alive.

Run as a script to list every event and what it does with empty saved facts:

    python -I scripts/reference/nights.py <data dir>

where <data dir> is extracted/art/assets/data.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tabtree  # noqa: E402
import travspec as T  # noqa: E402
from news import haxe_sort  # noqa: E402

SAY, ADD, REMOVE, SET, GROUP, COMMAND, OTHER = "say", "add", "remove", "set", "group", "command", "other"
MUST_PAY, OPTIONAL_YES, OPTIONAL_NO = "YES", "OPTIONAL_DEFAULTYES", "OPTIONAL_DEFAULTNO"
ESCAPE_ORDER = ["son", "wife", "niece", "uncle", "mil"]
UPGRADES = ["INSPECT_HOTKEY", "INSPECT_DOUBLECLICK", "RULEBOOK_TABS", "STAMPBAR_HOTKEY", "BOOTH_MULTITOUCH"]


class Op:
    def __init__(self, kind, text="", value=None, ops=None):
        self.kind, self.text, self.value, self.ops = kind, text, value, ops or []


def make_op(node):
    """OpHelper.makeOp without a root (so INCLUDE lines are not expanded)."""
    ops = [make_op(child) for child in node.nodes]
    sign, rest = node.params[0], " ".join(node.params[1:])
    if sign == '"':
        return Op(SAY, rest)
    if sign == "+":
        return Op(ADD, rest)
    if sign == "-":
        return Op(REMOVE, rest)
    if sign == "@":
        return Op(COMMAND, rest)
    if sign == "=":
        return Op(SET, node.params[1], node.params[2] if len(node.params) > 2 else None)
    if sign in ("!", "^", "\\"):
        return Op(OTHER, rest, ops=ops)
    if sign == "?":
        return Op(GROUP, " ".join(node.params), ops=ops)        # the name keeps its "?"
    return Op(GROUP, rest, ops=ops)                               # ">" lines and the entry itself


def get_run_ops(op, name):
    """OpHelper.getRunOps for groups: the first group, depth first, with
    that name. (Names with * are patterns; none occur in Nights.txt.)"""
    if op is None or op.kind != GROUP:
        return None
    if name is None or op.text == name:
        return op.ops
    for child in op.ops:
        found = get_run_ops(child, name)
        if found is not None:
            return found
    return None


class NightLib:
    def __init__(self, nights_text):
        self.events = {}
        for node in tabtree.parse(nights_text).nodes:
            self.events[node.params[0]] = get_run_ops(make_op(node), None)

    def find_event(self, event_id):
        if event_id not in self.events:
            raise KeyError("Night event not found: " + event_id)
        return self.events[event_id]


class Calendar:
    """Events waiting for a later night. Saved as "day:event;day:event"."""

    def __init__(self, lib, text=""):
        self.lib = lib
        self.entries = []
        for piece in (text.split(";") if text else []):
            parts = piece.split(":")
            if len(parts) == 2 and lib.find_event(parts[1]) is not None:
                self.entries.append((T.parse_int(parts[0]), parts[1]))

    def add_event(self, day_id, event_id):
        self.lib.find_event(event_id)
        self.entries.append((day_id, event_id))

    def get_events(self, day_id):
        return [event_id for day, event_id in self.entries if day == day_id]

    def to_string(self):
        return ";".join("%d:%s" % entry for entry in self.entries)


class Line:
    def __init__(self, name, cost, must_pay, yes_no_op):
        self.name, self.cost, self.must_pay, self.yes_no_op = name, cost, must_pay, yes_no_op
        self.enabled = must_pay in (MUST_PAY, OPTIONAL_YES)

    @property
    def rename_sleep_button(self):
        for op in get_run_ops(self.yes_no_op, "YES") or []:
            if op.kind == COMMAND and op.text.startswith("RenameSleepButton"):
                return op.text[len("RenameSleepButton"):].strip()
        return None


def compare_lines(a, b):
    """Income before costs; among those, lines that must be paid first."""
    if a.cost > 0 and b.cost < 0:
        return -1.0
    if a.cost < 0 and b.cost > 0:
        return 1.0
    if a.must_pay == MUST_PAY and b.must_pay != MUST_PAY:
        return -1.0
    if a.must_pay != MUST_PAY and b.must_pay == MUST_PAY:
        return 1.0
    return 0.0


class Budget:
    def __init__(self):
        self.lines = []

    def add_line(self, name, cost, must_pay=None, yes_no_op=None):
        if must_pay is None:
            must_pay = OPTIONAL_YES if cost < 0 else MUST_PAY
        self.lines.append(Line(name, cost, must_pay, yes_no_op))
        if len(self.lines) > 1:
            haxe_sort(self.lines, compare_lines)       # the game's sort; it reorders equal lines


class Night:
    """The event-running side of play.night.Family for one night."""

    def __init__(self, lib, story_facts, day_id, alive=()):
        self.lib = lib
        self.facts = story_facts
        self.day_id = day_id                      # the day that just ended
        self.alive = list(alive)                  # ids of living family members
        self.messages = []
        self.budget = Budget()
        self.calendar = Calendar(lib, story_facts.get("Night/Calendar", ""))
        self.want_end_id = None
        self.upgrades = []
        self.son_mood = None
        self.achievements = []
        self.escape = None

    # facts in the saved story
    def text(self, path):
        return self.facts.get(path, "")

    def number(self, path):
        return T.parse_int(self.facts.get(path, ""))

    def _list(self, path):
        return self.facts[path].split(";") if self.facts.get(path) else []

    def apply_event_with_id(self, event_id):
        for op in self.lib.find_event(event_id):
            self.apply_op(op)

    def apply_rent_and_heat_affecting_events(self, event_ids):
        """Run early only the top-level lines that set the rent or the heat."""
        for event_id in event_ids:
            for op in self.lib.find_event(event_id):
                if op.kind == SET and op.text in ("Night/Rent", "Night/Heat"):
                    self.apply_op(op)

    def apply_yes_no(self):
        """The part of applyBudget that runs each line's YES or NO lines."""
        for line in list(self.budget.lines):
            if line.yes_no_op is not None:
                for op in get_run_ops(line.yes_no_op, "YES" if line.enabled else "NO") or []:
                    self.apply_op(op)

    def apply_op(self, op):
        after = []
        if op.kind == SAY:
            self.messages.append(op.text)
        elif op.kind == ADD:                               # "+ days EVENT": schedule an event
            parts = op.text.split(" ")
            self.calendar.add_event(self.day_id + T.parse_int(parts[0]), parts[1])
        elif op.kind == SET:
            value = op.value
            if value.startswith("++"):
                self.facts[op.text] = str(self.number(op.text) + T.parse_int(value[2:]))
            elif value.startswith("--"):
                self.facts[op.text] = str(self.number(op.text) - T.parse_int(value[2:]))
            else:
                self.facts[op.text] = value
        elif op.kind == GROUP:
            if op.text.startswith("?"):
                tokens = tabtree.split_quoted(op.text[1:])
                if T.test_with_glue(tokens, 0, self.text):
                    after = op.ops
            else:
                parts = T.split_and_trim(op.text, "|")
                if len(parts) < 2:
                    raise ValueError("Invalid Night budget item: " + op.text)
                third = parts[2] if len(parts) > 2 else None
                must_pay = {"MUSTPAY": MUST_PAY, "NO": OPTIONAL_NO, "YES": OPTIONAL_YES}.get(third)
                self.budget.add_line(parts[0], T.parse_int(parts[1]), must_pay, op if op.ops else None)
        elif op.kind == COMMAND:
            self._command(op.text)
        for later in after:
            self.apply_op(later)

    def _command(self, text):
        if text == "MakeSonSad" or text == "MakeSonHappy":
            if "son" in self.alive:
                self.son_mood = "SAD" if text == "MakeSonSad" else "HAPPY"
        elif text.startswith("Upgrade-") and text[len("Upgrade-"):] in UPGRADES:
            self.upgrades.append(text[len("Upgrade-"):])
        elif text == "AdoptNiece":
            self.facts["Night/HaveNiece"] = "1"           # the fact name is set in the Family constructor (not read yet)
        elif text == "RemoveSavings":
            self.facts["Night/Savings"] = "0"             # also updates the savings budget line
        elif text == "TakeFamilyPassports":
            self.facts["Night/HaveFamilyPassports"] = "0"  # fact name as above: not read yet
        elif text.startswith("GivePaper"):
            path = "Night/Papers%d" % self.day_id
            papers = self._list(path)
            paper = text[len("GivePaper"):].strip()
            if paper not in papers:
                papers.append(paper)
            self.facts[path] = ";".join(papers)
        elif text.startswith("TakePaper"):
            papers = self._list("Game/StayingPapers")
            paper = text[len("TakePaper"):].strip()
            if paper in papers:
                papers.remove(paper)
            self.facts["Game/StayingPapers"] = ";".join(papers)
        elif text.startswith("End") and self.want_end_id is None:
            self.want_end_id = text[len("End"):].strip()
        elif text.startswith("Include"):
            self.apply_event_with_id(text[len("Include"):].strip())
        elif text.startswith("Achievement"):
            self.achievements.append(text[len("Achievement"):].strip())
        elif text.startswith("Escape"):
            count = T.parse_int(text[len("Escape"):].strip())
            candidates = [m for m in ESCAPE_ORDER if m in self.alive]
            taken, left = candidates[:max(0, count - 1)], candidates[max(0, count - 1):]
            self.escape = (taken, left)
            self.want_end_id = "flee" if left else "escape"
            self.facts["End/FamilyPassportsImage"] = "Passport%d.png" % (len(taken) + 1)
            self.facts["End/FamilyTakeCount"] = str(len(taken))
            # End/FamilyEscapeIntro and End/FamilyEscapeFinal are built by
            # Family.buildMessage from the text entries (not studied).
        # anything else (for example RenameSleepButton) does nothing here


def describe(ops, depth=1):
    for op in ops:
        label = {SAY: '"', ADD: "+", REMOVE: "-", SET: "=", COMMAND: "@", OTHER: "?!"}.get(op.kind, ">")
        text = op.text + (" " + op.value if op.kind == SET else "")
        print("    " * depth + label + " " + text)
        describe(op.ops, depth + 1)


def main():
    text = open(os.path.join(sys.argv[1], "Nights.txt"), encoding="utf-8", newline="").read()
    lib = NightLib(text)
    print("%d events" % len(lib.events))
    for event_id in lib.events:
        night = Night(lib, {}, 10, alive=ESCAPE_ORDER)
        night.apply_event_with_id(event_id)
        print("%s" % event_id)
        for message in night.messages:
            print('    says: %s' % message)
        for line in night.budget.lines:
            print("    budget line: %s %+d (%s%s)" % (line.name, line.cost, line.must_pay,
                                                     ", has YES/NO lines" if line.yes_no_op else ""))
        if night.calendar.entries:
            print("    schedules:", night.calendar.to_string())
        if night.facts:
            print("    facts:", night.facts)
        if night.want_end_id:
            print("    wants ending:", night.want_end_id)


if __name__ == "__main__":
    main()
