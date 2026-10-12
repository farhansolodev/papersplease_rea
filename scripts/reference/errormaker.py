"""Reference implementation of how a traveler's error is chosen.

Layer 4 of the traveler answer key: data.ErrorLib, data.Error (the parts
that decide whether an error is possible), data.ErrorContext,
data.ErrorMaker.makeError, and the error steps of
play.day.BoothEnv.makeNewTraveler (the first error, the roll for an
additional one, the "always" errors). See docs/errors-txt-format.md and
docs/traveler-creation.md.

What an error then does to the documents (its invalidate lines) belongs to
the next layer.

Run as a script to list the first error of a day's first travelers:

    python -I scripts/reference/errormaker.py <master seed> <day> <count> <data dir>

The demonstration uses the booth's generator for errors only. In the game
the person and the documents draw from it between two errors, so **these are
not the errors the game would produce for that seed**.
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tabtree  # noqa: E402
import travspec as T  # noqa: E402
from cyclers import FaceCycler  # noqa: E402
from rand import Rand  # noqa: E402
from seeds import Launch, day_seeds  # noqa: E402

RECENT_GROUPS_MAX = 5


class Error:
    def __init__(self, node):
        self.id = node.params[0]
        self.group = node.params[1] if len(node.params) > 1 else self.id
        self.node = node
        # Only requirements directly under the error count.
        self.requirements = [child.params[1:] for child in node.nodes if child.params[0] == "\\"]
        self.invalidates = [child.params[1] for child in node.nodes if child.params[0] == "!"]

    def hidden_paper_id(self):
        if "-" in self.id and "-Hidden" in self.id:
            return self.id[:self.id.index("-")]
        return None

    def is_speech_error(self):
        return "<speech>" in self.id

    def matches(self, context):
        for tokens in self.requirements:
            if len(tokens) == 1:
                if tokens[0] not in context.paper_ids:
                    return False
            elif len(tokens) >= 3:
                if not T.test_with_glue(tokens, 0, context.expand):
                    return False
        return True


class ErrorLib:
    def __init__(self, errors_text):
        root = tabtree.parse(errors_text)
        tabtree.expand_params(root)
        self.random_errors = []
        self.always_errors = []
        for node in root.nodes:
            if not node.params or node.params[0].startswith("*"):
                continue
            error = Error(node)
            (self.always_errors if error.id.startswith("ALWAYS") else self.random_errors).append(error)

    def find(self, error_id):
        for error in self.random_errors:
            if error.id == error_id:
                return error
        return None

    def errors_for_context(self, patterns, context):
        """Each space-separated piece is a case-insensitive pattern; an
        error is kept when any pattern is found in its id."""
        regs = [re.compile(piece, re.IGNORECASE) for piece in patterns.split(" ")]
        return [error for error in self.random_errors
                if error.group not in context.ignore_groups
                and any(reg.search(error.id) for reg in regs)
                and error.matches(context)]

    def always_errors_for_context(self, context):
        return [error for error in self.always_errors if error.matches(context)]


class ErrorContext:
    def __init__(self, paper_ids, data):
        self.paper_ids = paper_ids             # the specification's own list, not a copy
        self.data = data
        self.ignore_groups = []

    def expand(self, left):
        return self.data[left] if left in self.data else left

    def add_to_filter(self, text):
        self.data["FILTER"] = (self.data.get("FILTER") or "") + ";" + text


def make_error_context(day_facts, spec, confiscation_id):
    v = spec.vars
    return ErrorContext(spec.initial_papers, {
        "FEATURES": day_facts.get("Day/Features", ""),
        "RULES": day_facts.get("Day/Rules", ""),
        "NATION": v.get("nation"),
        "PURPOSE": v.get("purpose"),
        "DISTRICT": v.get("district"),
        "CONFISCATION": confiscation_id,
        "FILTER": "",
    })


class ErrorMaker:
    """One per booth, so "recent" spans every traveler of the day."""

    def __init__(self, rand, lib):
        self.rand = rand
        self.lib = lib
        self.recent_groups = []                # newest first

    def _pick(self, groups):
        group = groups[int(len(groups) * self.rand.random())]
        return group[int(len(group) * self.rand.random())]

    def make_error(self, patterns, context):
        candidates = self.lib.errors_for_context(patterns, context)
        if not candidates:
            return None                        # and no draw
        by_group = {}
        groups = []
        for error in candidates:
            if error.group not in by_group:
                by_group[error.group] = []
                groups.append(by_group[error.group])
            by_group[error.group].append(error)
        for recent in self.recent_groups:
            if len(groups) < 2:
                break
            if recent in by_group:
                groups.remove(by_group.pop(recent))
        error = self._pick(groups)
        if "<rare>" in error.id and self.rand.random() < 0.5:
            error = self._pick(groups)
        self.recent_groups.insert(0, error.group)
        if len(self.recent_groups) >= RECENT_GROUPS_MAX:
            # Removes the first entry equal to the oldest one.
            self.recent_groups.remove(self.recent_groups[-1])
        return error


def first_error(spec, context, maker):
    """Step 5 of makeNewTraveler: only when the script set `error`."""
    patterns = spec.vars.get("error")
    return maker.make_error(patterns, context) if patterns is not None else None


def additional_error(spec, error, context, maker, rand, misc):
    """Step 11 of makeNewTraveler. `error` is the traveler's error after the
    person was built (the constructor can replace or drop it)."""
    if error is None or spec.custom_error is not None:
        return None
    if spec.vars.get(T.ERROR_SET_RANDOMLY) != "YES" or spec.vars.get("preventAdditionalError") is not None:
        return None
    context.add_to_filter("ADDITIONAL")
    context.ignore_groups.append(error.group)
    hidden = error.hidden_paper_id()
    if hidden is None:
        if error.is_speech_error():
            if rand.random() < T.parse_float(misc["speechAdditionalErrorPerc"]):
                return maker.make_error("<generic>", context)
        return None
    if rand.random() < T.parse_float(misc["hiddenAdditionalErrorPerc"]):
        # A new context: only the hidden paper, the same table, no ignored groups.
        return maker.make_error("<generic>", ErrorContext([hidden], context.data))
    return None


def load_misc(facts_xml_text):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(re.sub(r"&(?!(amp|lt|gt|quot|apos);)", "&amp;", facts_xml_text))
    return dict(root.find("misc").attrib)


def main():
    master, day_number, count = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    data_dir = sys.argv[4]
    read = lambda name: open(os.path.join(data_dir, name), encoding="utf-8", newline="").read()
    table, world, root = T.load(data_dir)
    lib = ErrorLib(read("Errors.txt"))
    misc = load_misc(read("Facts.xml"))
    launch = Launch(master)
    day = T.Day(table, day_number, launch.story_seed, FaceCycler(launch.face_cycler_seed))
    booth = Rand(day_seeds(day_number, launch.story_seed)["booth"])
    maker = ErrorMaker(booth, lib)
    context_maker = T.TravelerContext(root, world, day.facts)
    confiscation = table.cell(day_number, "CONFISCATE").replace("&amp;", "&") or None
    print("master %d, day %d | random errors: %d, always errors: %d | misc: %s" % (
        master, day_number, len(lib.random_errors), len(lib.always_errors), misc))
    print("NOT what the game would produce: the person's and the documents' draws are missing.")
    for _ in range(count):
        entry = day.next_traveler_id()
        spec = context_maker.make_spec(entry, day.traveler_rand)
        context = make_error_context(day.facts, spec, confiscation)
        candidates = (lib.errors_for_context(spec.vars["error"], context)
                      if spec.vars.get("error") is not None else [])
        error = first_error(spec, context, maker)
        second = additional_error(spec, error, context, maker, booth, misc)
        always = lib.always_errors_for_context(context)
        print("%-20s %-9s %-9s error var: %-28s candidates: %3d -> %s%s%s" % (
            entry, spec.vars.get("nation"), spec.vars.get("purpose"), spec.vars.get("error"),
            len(candidates), error.id if error else "none",
            " + " + second.id if second else "",
            " | always: " + ",".join(e.id for e in always) if always else ""))


if __name__ == "__main__":
    main()
