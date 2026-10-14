"""Reference implementation of night events: data.NightLib, data.NightEvent,
play.night.Calendar, and the parts of play.night.Family and
play.night.Budget that run an event's lines (docs/nights-txt-format.md).

`Night` runs single events (a caller supplies who is alive). `Family` is the
whole night: the family members and their health, the standard budget lines,
which events run and in what order, balancing and applying the budget
(docs/night.md).

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

    def update_line_cost(self, name, cost):
        for line in self.lines:
            if line.name == name:
                line.cost = cost

    def will_pay(self, name):
        """Is the first line with this name ticked? False when there is none."""
        for line in self.lines:
            if line.name == name:
                return line.enabled
        return False

    @property
    def total(self):
        """What is left after every ticked line."""
        return sum(line.cost for line in self.lines if line.enabled)

    @property
    def profit(self):
        """Income plus the costs that cannot be avoided."""
        return sum(line.cost for line in self.lines if line.cost > 0 or line.must_pay == MUST_PAY)

    def balance(self):
        """Untick optional lines from the bottom up until the total is not
        negative. Returns the index of the last line unticked, or None."""
        rejected = None
        count = len(self.lines)
        for i in range(count):
            if self.total >= 0:
                return rejected
            line = self.lines[count - i - 1]
            if line.must_pay != MUST_PAY and line.enabled:
                line.enabled = False
                rejected = count - i - 1
        return rejected


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

    savings_line_name = "SAVINGS"

    def alive_ids(self):
        return self.alive

    def set_son_mood(self, mood):
        self.son_mood = mood

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
            if "son" in self.alive_ids():
                self.set_son_mood("SAD" if text == "MakeSonSad" else "HAPPY")
        elif text.startswith("Upgrade-") and text[len("Upgrade-"):] in UPGRADES:
            self.upgrades.append(text[len("Upgrade-"):])
        elif text == "AdoptNiece":
            self.facts["Night/HaveNiece"] = "1"
        elif text == "RemoveSavings":
            self.facts["Night/Savings"] = "0"
            self.budget.update_line_cost(self.savings_line_name, 0)
        elif text == "TakeFamilyPassports":
            self.facts["Night/HaveFamilyPassports"] = "0"
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
            candidates = [m for m in ESCAPE_ORDER if m in self.alive_ids()]
            taken, left = candidates[:max(0, count - 1)], candidates[max(0, count - 1):]
            self.escape = (taken, left)
            self.want_end_id = "flee" if left else "escape"
            self.facts["End/FamilyPassportsImage"] = "Passport%d.png" % (len(taken) + 1)
            self.facts["End/FamilyTakeCount"] = str(len(taken))
            # End/FamilyEscapeIntro and End/FamilyEscapeFinal are built by
            # Family.buildMessage from the text entries (see build_message).
        # anything else (for example RenameSleepButton) does nothing here


# ---------------------------------------------------------------- the whole night

MEMBERS = [  # id, most sick, most hungry, most cold, male
    ("wife", 5, 2, 3, False), ("son", 4, 1, 3, True), ("mil", 4, 2, 4, False), ("uncle", 3, 3, 3, True)]
NIECE = ("niece", 4, 2, 3, False)
EMOTIONS = ["HAPPY", "OK", "SAD", "COLD", "SICK", "VERYSICK", "DEAD", "HUNGRY"]
ATTACK_EVENTS = {"FAILED_DIDNOTHING": "ATTACK_DIDNOTHING", "FAILED_FIREDGUN": "ATTACK_FIREDGUN",
                 "SOLVED": "ATTACK_SOLVED"}


class Member:
    def __init__(self, member_id, sick_max, hungry_max, cold_max, male):
        self.id, self.male = member_id, male
        self.value = {"sick": 0, "hungry": 0, "cold": 0}
        self.most = {"sick": sick_max, "hungry": hungry_max, "cold": cold_max}
        self.just_died = False
        self.mood = None

    @property
    def alive(self):
        return self.value["sick"] < self.most["sick"]

    @property
    def sick(self):
        return self.value["sick"] > 0

    @property
    def very_sick(self):
        return self.value["sick"] >= self.most["sick"] - 1

    def adjust(self, stat, delta):
        """One step up or down whatever the size of delta; nothing if dead."""
        if not self.alive or stat not in self.value:
            return
        if delta < 1:
            self.value[stat] = max(0, self.value[stat] - 1)
        else:
            self.value[stat] = min(self.most[stat], self.value[stat] + 1)

    def update_sickness(self):
        if not self.alive:
            self.just_died = False
            return
        for stat in ("hungry", "cold"):
            if self.value[stat] >= self.most[stat]:
                self.value["sick"] = min(self.most["sick"], self.value["sick"] + 1)
        self.mood = None
        if not self.alive:
            self.just_died = True

    def emotions(self):
        """FamilyMember.get_emotionFlags as a list of names."""
        if not self.alive:
            return ["DEAD"]
        out = []
        if self.value["hungry"] >= 1:
            out.append("HUNGRY")
        if self.value["cold"] >= 1:
            out.append("COLD")
        if self.very_sick:
            out.append("VERYSICK")
        elif self.sick:
            out.append("SICK")
        if self.mood:
            out.append(self.mood)
        return out or ["OK"]

    def to_string(self):
        """The saved form. The game writes the same pairs through a lookup
        table, so their order in the real save may differ."""
        pairs = [("hungry", self.value["hungry"]), ("cold", self.value["cold"]), ("sick", self.value["sick"]),
                 ("justDied", str(self.just_died).lower()), ("alive", str(self.alive).lower())]
        if self.mood:
            pairs.append(("moodEmotion", self.mood))
        return " ".join("%s=%s" % pair for pair in pairs)

    def from_string(self, text):
        pairs = dict(piece.split("=", 1) for piece in text.split(" ") if "=" in piece)
        for stat in self.value:
            if stat in pairs:
                self.value[stat] = T.parse_int(pairs[stat])
        if "justDied" in pairs:
            self.just_died = pairs["justDied"] == "true"
        self.mood = pairs.get("moodEmotion") if pairs.get("moodEmotion") in EMOTIONS else None


class Summary:
    """What the day hands to the night (play.day.Summary)."""

    def __init__(self, day_id, paid=0, unpaid=0, penalties=0, penalty_cost=0, bribe_money=0,
                 attack_result="NONE", had_attack=False, had_bomber=False, had_poisoning=False,
                 token_ids=(), night_event_ids=(), escape_passports=0):
        self.id, self.paid, self.unpaid = day_id, paid, unpaid
        self.penalties, self.penalty_cost, self.bribe_money = penalties, penalty_cost, bribe_money
        self.attack_result, self.had_attack, self.had_bomber = attack_result, had_attack, had_bomber
        self.had_poisoning = had_poisoning
        self.token_ids, self.night_event_ids = list(token_ids), list(night_event_ids)
        self.escape_passports = escape_passports


def fill(template, *values):
    for index, value in enumerate(values):
        template = template.replace("$%d" % index, str(value))
    return template


class Family(Night):
    """play.night.Family: built when the day ends; apply_budget runs when the
    player goes to sleep."""

    def __init__(self, lib, story_facts, summary, texts, night_messages=(), num_days=31, easy_mode=False):
        self.lib, self.facts, self.summary, self.texts = lib, story_facts, summary, texts
        self.day_id, self.num_days = summary.id, num_days
        self.want_end_id = None
        self.upgrades, self.achievements, self.escape, self.son_mood = [], [], None, None
        self.messages = []
        self.budget = Budget()
        self.calendar = Calendar(lib)             # not used by the first step; replaced below
        self.members = []
        self.apply_rent_and_heat_affecting_events(summary.night_event_ids)
        self.calendar = Calendar(lib, self.text("Night/Calendar"))
        definitions = MEMBERS + ([NIECE] if self.number_or("Night/HaveNiece", 0) != 0 else [])
        self.members = [Member(*definition) for definition in definitions]
        for member in self.members:
            member.from_string(self.text("Night/" + member.id))
        self.facts["Night/AttackResult"] = summary.attack_result

        t = texts
        self.savings_line_name = t["budget_savings"]
        add = self.budget.add_line
        add(t["budget_savings"], self.number_or("Night/Savings", 30))
        add(fill(t["budget_salary"], summary.paid), summary.paid * 5)
        if summary.penalties != 0:
            add(fill(t["budget_penalties"], summary.penalties), -summary.penalty_cost, MUST_PAY)
        if summary.bribe_money != 0:
            add(t["budget_bribes"], summary.bribe_money)
        add(t["budget_rent"], self.number_or("Night/Rent", -20), MUST_PAY)
        add(t["budget_food"], len(self.alive_ids()) * -5)
        add(t["budget_heat"], self.number_or("Night/Heat", -10))
        for member in self.members:
            if member.alive and member.sick:
                add(self.medicine_name(member), -5)

        if summary.attack_result == "NONE":
            if summary.had_attack or summary.had_bomber:
                self.apply_event_with_id("ATTACK_DIDNOTHING")
        elif summary.attack_result in ATTACK_EVENTS:
            self.apply_event_with_id(ATTACK_EVENTS[summary.attack_result])
        if summary.had_poisoning:
            self.apply_event_with_id("POISONING")
        died = [m for m in self.members if m.just_died]
        sick = [m for m in self.members if m.alive and m.sick]
        very_sick = [m for m in self.members if m.alive and m.very_sick]
        self.messages += list(night_messages)
        if self.number_or("Night/Flags", 0) & 1 == 0 and summary.unpaid != 0:
            self.apply_event_with_id("AFTER_6PM")
        if died:
            self.messages.append(self.build_message("family_died_", died))
        if len(very_sick) == 1:
            self.messages.append(fill(t["family_verysick_1"], self.message_name(very_sick[0])))
        elif len(very_sick) > 1:
            self.messages.append(t["family_verysick_many"])
        elif len(sick) == 1:
            self.messages.append(fill(t["family_sick_1"], self.message_name(sick[0])))
        elif len(sick) > 1:
            self.messages.append(t["family_sick_many"])
        self.facts["Night/NumEscapePassports"] = str(int(min(
            len(self.alive_ids()) + 1, summary.escape_passports + self.number_or("Night/NumEscapePassports", 0))))
        self.facts["Night/Profit"] = str(self.budget.profit)
        for event_id in summary.night_event_ids:
            self.apply_event_with_id(event_id)
        for event_id in self.calendar.get_events(summary.id):
            self.apply_event_with_id(event_id)
        if easy_mode:
            self.apply_event_with_id("EASY_MODE")

    def number_or(self, path, default):
        return T.parse_int(self.facts[path]) if self.facts.get(path) else default

    def alive_ids(self):
        return [m.id for m in self.members if m.alive]

    def set_son_mood(self, mood):
        self.son_mood = mood
        next(m for m in self.members if m.id == "son").mood = mood

    def message_name(self, member):
        return self.texts["family_%s_message" % member.id]

    def medicine_name(self, member):
        return fill(self.texts["budget_medicine"], self.texts["family_%s_budget" % member.id])

    def build_message(self, prefix, members):
        """Family.buildMessage (read on 2026-10-14, docs/screens.md part 1):
        the text prefix + count, $0.. the members' message names. Left out:
        the [m0]..[/m0] and [f0]..[/f0] tags and the gender switches, which
        the English texts do not use, and a missing text giving ""."""
        return fill(self.texts[prefix + str(len(members))], *[self.message_name(m) for m in members])

    def apply_budget(self):
        tokens = self._list("Night/TokenIds")
        for token in self.summary.token_ids:
            if token not in tokens:
                tokens.append(token)
        self.facts["Night/TokenIds"] = ";".join(tokens)
        if self.summary.unpaid != 0:
            self.facts["Night/Flags"] = str(self.number_or("Night/Flags", 0) | 1)
        self.facts["Night/Savings"] = str(self.budget.total)
        heat = -1 if self.budget.will_pay(self.texts["budget_heat"]) else 1
        food = -1 if self.budget.will_pay(self.texts["budget_food"]) else 1
        for member in self.members:
            member.adjust("cold", heat)
        for member in self.members:
            member.adjust("hungry", food)
        for member in self.members:
            if self.budget.will_pay(self.medicine_name(member)):
                member.adjust("sick", -1)
        self.apply_yes_no()
        for member in self.members:
            member.update_sickness()
        self.facts["Night/Calendar"] = self.calendar.to_string()
        self.facts["Night/FamilyAlive"] = str(len(self.alive_ids()))
        for member in self.members:
            self.facts["Night/" + member.id] = member.to_string()
        if self.summary.id == self.num_days:
            self.apply_event_with_id("FINAL")
        if self.want_end_id is None:
            if self.budget.total < 0:
                self.want_end_id = "in-debt"
            elif not self.alive_ids():
                self.want_end_id = "family-dead"


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
