"""Reference implementation of turning a traveler script into a specification.

Layer 3 of the traveler answer key: play.day.TravelerContext
(makeTravelerSpec, applyToSpec, assignVar, the condition tester), the random
pickers of data.WorldDef that fill in what a script leaves unset, the parts
of Days.csv that decide who comes next, and the part of the day's set-up
that uses the same random generator (the three "criminal" faces).
See docs/travelers-txt-format.md, docs/traveler-creation.md and
docs/days-csv-format.md.

Run as a script to list the first travelers of a day:

    python -I scripts/reference/travspec.py <master seed> <day> <count> <data dir>

where <data dir> is extracted/art/assets/data.
"""

import csv
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tabtree  # noqa: E402
from cyclers import FaceCycler, NUM_PALETTES  # noqa: E402
from rand import Rand  # noqa: E402
from seeds import Launch, day_seeds  # noqa: E402

ERROR_SET_RANDOMLY = "error_setRandomly"


# ---------------------------------------------------------------- random helpers

def pick(rand, items):
    """ArrayUtil.getRandomItem: one draw; nothing if the draw is exactly 1.0."""
    index = int(len(items) * rand.random())
    return items[index] if index < len(items) else None


def weighted_pick(rand, choices):
    """app.Probability.select: choices are (value, weight); one draw."""
    total = 0.0
    for _, weight in choices:
        total += weight
    r = rand.random()
    running = 0.0
    for value, weight in choices:
        running += weight
        if r * total < running:
            return value
    return None


def parse_float(text):
    """Std.parseFloat for the values that occur here: the leading number."""
    match = re.match(r"\s*[-+]?(\d+\.?\d*([eE][-+]?\d+)?|\.\d+)", text)
    return float(match.group(0)) if match else float("nan")


def parse_int(text):
    """Std.parseInt: the leading whole number, 0 when there is none."""
    match = re.match(r"\s*[-+]?\d+", text or "")
    return int(match.group(0)) if match else 0


def split_and_trim(text, delimiter):
    """StringUtil.splitAndTrim: split, trim each piece, drop empty ones."""
    return [piece.strip() for piece in (text or "").split(delimiter) if piece.strip()]


# ---------------------------------------------------------------- Days.csv

class DaysTable:
    """The sideways table: each row a property, each column a day."""

    def __init__(self, text):
        rows = [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(text))]
        rows = [row for row in rows if row]
        self.col_ids = rows[0]
        self.rows = {row[0]: row for row in rows}

    def cell(self, col_id, row_id):
        row = self.rows[row_id]
        index = self.col_ids.index(str(col_id))
        return row[index] if index < len(row) else ""

    def accumulated(self, through_col, row_id):
        """CsvTable.getAccumulatedRow: +Name stays, -Name removes, a plain
        name counts only in the requested column."""
        through_col = str(through_col)
        out = []
        for col_id in self.col_ids:
            for item in split_and_trim(self.cell(col_id, row_id), "\n"):
                if item.startswith("+"):
                    out.append(item[1:])
                elif item.startswith("-"):
                    if item[1:] in out:
                        out.remove(item[1:])
                elif col_id == through_col:
                    out.append(item)
            if col_id == through_col:
                break
        return out


class Day:
    """The parts of play.day.Day that decide who comes next."""

    def __init__(self, table, day, story_seed, face_cycler, story_facts=None):
        self.id = day
        self.traveler_rand = Rand(day_seeds(day, story_seed)["traveler"])
        story_facts = story_facts or {}
        self.traveler_ids = split_and_trim(table.cell(day, "TRAVELERS"), "\n")
        fill = table.cell(day, "FILL")
        if fill:
            self.traveler_ids.append(fill)
        # Not confirmed that the number in Game/Visitor<n> is the day.
        visitor = story_facts.get("Game/Visitor%d" % day)
        if visitor:
            self.traveler_ids.insert(0, visitor)
        rules = table.accumulated(day, "RULES")
        features = table.accumulated(day, "FEATURES")
        self.facts = {
            "Day/Rules": "".join(rule + ";" for rule in rules),
            "Day/Id": str(day),
            "Day/Features": ";".join(features) + ";",
        }
        self.num_made = 0
        # Every day starts by making three "criminals", whether or not the
        # day shows them: a scripted face from CRIMFACE if there is one, then
        # faces from the face cycler, one draw each for the gender.
        self.criminals = []
        match = re.match(r"\s*(.*):(.*)\s*", table.cell(day, "CRIMFACE").strip())
        if match:
            self.criminals.append((match.group(1), face_spec_from_string(self.traveler_rand,
                                                                         match.group(2))))
        while len(self.criminals) < 3:
            male = self.traveler_rand.random() > 0.5
            self.criminals.append((None, face_cycler.next(male)))

    def next_traveler_id(self):
        index = min(len(self.traveler_ids) - 1, self.num_made)
        self.num_made += 1
        return self.traveler_ids[index]


def face_spec_from_string(rand, text):
    """FaceSpec.fromString: one draw for each part that is missing or '*'."""
    parts = text.split("-")

    def given(index):
        return index < len(parts) and parts[index] != "*"

    male = parts[0] == "M" if given(0) else rand.random() > 0.5
    pieces = [parse_int(parts[i]) if given(i) else int(20 * rand.random()) for i in range(1, 5)]
    palette = parse_int(parts[5]) if given(5) else int(NUM_PALETTES * rand.random())
    flip = bool(parse_int(parts[6]) & 1) if given(6) else rand.random() > 0.5
    return (male, pieces[0], pieces[1], pieces[2], pieces[3], palette, flip)


# ---------------------------------------------------------------- Facts.xml world

class World:
    """The world sections of Facts.xml, in file order."""

    def __init__(self, facts_xml_text):
        root = ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos);)", "&amp;", facts_xml_text))
        section = lambda name, tag: root.find(name).findall(tag)
        self.nations = [(n.get("name"), n.get("cities").split(";")) for n in section("nations", "nation")]
        self.purposes = [{
            "id": p.get("val"),
            "chance": parse_float(p.get("chance")) if p.get("chance") is not None else 1.0,
            "rule": p.get("rule"),
            "nations": split_and_trim(p.get("nations"), " "),
            "choose_for_invalid": p.get("chooseforinvalid") is None or p.get("chooseforinvalid") == "true",
        } for p in section("purposes", "purpose")]
        self.autopapers = [{
            "id": a.get("id"),
            "rule": a.get("rule"),
            "purposes": split_and_trim(a.get("purposes"), " ") if a.get("purposes") is not None else None,
        } for a in section("autopapers", "autopaper")]
        self.durations = [(d.get("val"), d.get("purposes")) for d in section("durations", "duration")]
        self.districts = [d.get("val") for d in section("districts", "district")]
        self.jobs = [j.get("val") for j in section("jobs", "job")]

    def random_nationality(self, rand, purpose):
        if purpose is None:
            nation = pick(rand, self.nations)
            return nation[0] if nation else None
        for definition in self.purposes:
            if definition["id"] == purpose:
                return pick(rand, definition["nations"])
        raise ValueError("Unknown purpose: " + purpose)

    def random_purpose(self, rand, nation, rules, for_invalid=False):
        """The filter on error patterns is left out: with the game's data it
        excludes nothing (docs/facts-xml-format.md)."""
        choices = []
        for definition in self.purposes:
            if for_invalid and not definition["choose_for_invalid"]:
                continue
            if nation in definition["nations"] and (definition["rule"] is None
                                                    or definition["rule"] in rules):
                choices.append((definition["id"], definition["chance"]))
        return weighted_pick(rand, choices)

    def random_duration(self, rand, purpose):
        values = [value for value, purposes in self.durations
                  if purpose is None or purpose in (purposes or "")]
        return pick(rand, values)

    def random_issuing_city(self, rand, nation):
        for name, cities in self.nations:
            if name == nation:
                return pick(rand, cities)
        return "UNKNOWN"                       # no draw in this case

    def auto_paper_ids(self, purpose, rules):
        return [a["id"] for a in self.autopapers
                if (a["purposes"] is None or purpose in a["purposes"])
                and (a["rule"] is None or a["rule"] in rules)]


# ---------------------------------------------------------------- conditions

def test_one(left, op, right, expand):
    """app.ExpressionTester.test."""
    if left != "PASSTHROUGH" and expand is not None:
        value = expand(left)
        left = value if value is not None else ""
    left, right = left.lower(), right.lower()
    if op == "==":
        return left == right
    if op == "!=":
        return left != right
    if op == "has":
        return right in left
    if op == "!has":
        return right not in left
    if op in ("<", "<=", ">", ">="):
        a, b = parse_int(left), parse_int(right)
        return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}[op]
    return False                               # any other operator


def test_with_glue(tokens, start, expand):
    """Left to right, no precedence; || and && short-circuit."""
    if len(tokens) < start + 3:
        raise ValueError("Invalid conditional: " + " ".join(tokens))
    result = test_one(tokens[start], tokens[start + 1], tokens[start + 2], expand)
    glue = tokens[start + 3] if start + 3 < len(tokens) else None
    if glue == "||":
        if result:
            return True
    elif glue == "&&":
        if not result:
            return False
    else:
        return result
    return test_with_glue(tokens, start + 4, expand)


# ---------------------------------------------------------------- the script

class Spec:
    def __init__(self, entry_id):
        self.id = entry_id
        self.vars = {}
        self.initial_papers = []               # push adds at the front
        self.custom_fact_groups = []
        self.custom_error = None
        self.custom_error_node = None
        self.responses = []


class TravelerContext:
    def __init__(self, root, world, day_facts, story_facts=None):
        self.root = root
        self.world = world
        self.day_facts = day_facts
        self.story_facts = story_facts or {}

    def find(self, entry_id):
        return self.root.find(entry_id)

    def expand(self, left):
        if left.startswith("Day/"):
            return self.day_facts.get(left, "")
        if left.startswith("Game/") or left.startswith("Night/"):
            return self.story_facts.get(left, "")
        raise ValueError("Invalid TravelerContext lhs: " + left)

    def assign(self, rand, node, variables):
        params = node.params
        choices = []
        if not node.nodes:
            if len(params) == 0:
                return
            for token in params[2:]:
                colon = token.rfind(":")
                if colon < 0:
                    choices.append((token, 1.0))
                else:
                    choices.append((token[:colon], parse_float(token[colon + 1:])))
        else:
            for child in node.nodes:
                weight = parse_float(child.params[1])
                if child.params[0] != "x" or weight == 0.0:
                    raise ValueError("Invalid choice: " + " ".join(child.params))
                choices.append((" ".join(child.params[2:]), weight))
        name = params[1]
        if not choices:
            variables.pop(name, None)
            if name == "error":
                variables.pop(ERROR_SET_RANDOMLY, None)
            return
        variables[name] = weighted_pick(rand, choices)     # one draw even with one choice
        if name == "error" and len(choices) > 1:
            variables[ERROR_SET_RANDOMLY] = "YES"

    def apply(self, rand, spec, node):
        """applyToSpec. False means BREAK was reached: stop everything."""
        for child in node.nodes:
            params = child.params
            kind = params[0]
            if kind == "=":
                self.assign(rand, child, spec.vars)
            elif kind == "?":
                def expand(left):
                    if left == "RANDOM100":
                        return str(int(rand.random() * 100))
                    if "/" not in left:
                        return spec.vars.get(left)
                    return self.expand(left)
                if test_with_glue(params, 1, expand):
                    if not self.apply(rand, spec, child):
                        return False
            elif kind == "INCLUDE":
                included = self.find(params[1])
                if included is None:
                    raise ValueError("Included traveler not found: " + params[1])
                if not self.apply(rand, spec, included):
                    return False
            elif kind == "BREAK":
                return False
            elif kind == "+":
                spec.initial_papers.insert(0, params[1])
            elif kind == "-":
                if params[1] in spec.initial_papers:
                    spec.initial_papers.remove(params[1])
            elif kind == "MANUALPAPERS":
                spec.vars["MANUALPAPERS"] = "true"
            elif kind == ">":
                spec.responses.append(" ".join(params[1:]))
            elif kind == "(":
                spec.custom_fact_groups.append((params[1], [c.params[0] for c in child.nodes]))
            elif kind == "*":
                spec.custom_error = params[1]
                spec.custom_error_node = child
            else:
                raise ValueError("Unknown block node: " + " ".join(params))
        return True

    def make_spec(self, entry_id, rand):
        node = self.find(entry_id)
        if node is None:
            raise ValueError("Traveler not found: " + entry_id)
        spec = Spec(entry_id)
        self.apply(rand, spec, node)
        v = spec.vars
        if v.get("fallback") is not None:
            return self.make_spec(v["fallback"], rand)     # the first attempt is thrown away
        rules = self.day_facts.get("Day/Rules", "")
        if v.get("nation") is None:
            v["nation"] = self.world.random_nationality(rand, v.get("purpose"))
        if v.get("purpose") is None or v["purpose"] == "random":
            v["purpose"] = self.world.random_purpose(rand, v.get("nation"), rules)
        if v.get("job") is None:
            v["job"] = pick(rand, self.world.jobs)
        if v.get("district") is None:
            v["district"] = pick(rand, self.world.districts)
        if v.get("duration") is None:
            v["duration"] = self.world.random_duration(rand, v.get("purpose"))
        if v.get("issuingCity") is None:
            v["issuingCity"] = self.world.random_issuing_city(rand, v.get("nation"))
        else:
            v["issuingCity"] = v["issuingCity"].replace("-", " ")
        if v.get("gender") is None:
            v["gender"] = "M" if rand.random() > 0.5 else "F"
        else:
            v["genderForced"] = "YES"
        if v.get("MANUALPAPERS") != "true":
            for paper in self.world.auto_paper_ids(v.get("purpose"), rules):
                if paper not in spec.initial_papers:
                    spec.initial_papers.insert(0, paper)
        return spec


class CountingRand(Rand):
    def __init__(self, seed):
        self.count = 0
        super().__init__(seed)
        self.count = 0

    def next_int(self):
        self.count += 1
        return super().next_int()

    def next_float(self):
        return self.next_int() / 2147483647.0

    random = next_float


def load(data_dir):
    read = lambda name: open(os.path.join(data_dir, name), encoding="utf-8", newline="").read()
    return (DaysTable(read("Days.csv")), World(read("Facts.xml")),
            tabtree.parse(read("Travelers.txt")))


def main():
    master, day_number, count = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    table, world, root = load(sys.argv[4])
    launch = Launch(master)
    face_cycler = FaceCycler(launch.face_cycler_seed)
    day = Day(table, day_number, launch.story_seed, face_cycler)
    counting = CountingRand(0)
    counting.__dict__.update(day.traveler_rand.__dict__)       # carry on from the day's set-up
    counting.count = 0
    context = TravelerContext(root, world, day.facts)
    print("master %d, day %d, story seed %d" % (master, day_number, launch.story_seed))
    print("rules: %s | features: %s" % (day.facts["Day/Rules"], day.facts["Day/Features"]))
    print("traveler list: %s" % " ".join(day.traveler_ids))
    print("criminal faces made at the start of the day:",
          " ".join("%s-%d-%d-%d-%d-%d-%d" % (("M" if c[1][0] else "F",) + tuple(int(x) for x in c[1][1:]))
                   for c in day.criminals))
    for _ in range(count):
        entry = day.next_traveler_id()
        before = counting.count
        spec = context.make_spec(entry, counting)
        v = spec.vars
        show = " ".join("%s=%s" % (k, v[k]) for k in ("gender", "nation", "purpose", "duration",
                                                      "issuingCity", "district", "job") if k in v)
        extra = " ".join("%s=%s" % (k, v[k]) for k in sorted(v)
                         if k not in ("gender", "nation", "purpose", "duration", "issuingCity",
                                      "district", "job", "genderForced"))
        print("%-22s %s | papers: %s | %s (%d draws)" % (
            entry + (" -> " + spec.id if spec.id != entry else ""), show,
            ",".join(spec.initial_papers) or "-", extra or "-", counting.count - before))


if __name__ == "__main__":
    main()
