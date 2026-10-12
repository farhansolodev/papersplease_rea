"""Checks of scripts/reference/errormaker.py against the data files.

Usage: python -I errormaker_check.py <reference dir> <data dir>

Picks the first error (and rolls for a second) for the first travelers of
every story day and several master seeds, and checks the rules of
docs/errors-txt-format.md on the results.
"""
import collections
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import errormaker as E
import travspec as T
from cyclers import FaceCycler
from seeds import Launch, day_seeds

C = collections.Counter
data_dir = sys.argv[2]
read = lambda name: open(os.path.join(data_dir, name), encoding="utf-8", newline="").read()
table, world, root = T.load(data_dir)
lib = E.ErrorLib(read("Errors.txt"))
misc = E.load_misc(read("Facts.xml"))

print("-- the error library --")
print("  random errors:", len(lib.random_errors), "| always errors:", [e.id for e in lib.always_errors])
print("  groups among random errors:", len({e.group for e in lib.random_errors}))
hidden = {e.id: e.hidden_paper_id() for e in lib.random_errors if e.hidden_paper_id()}
print("  errors that hide a paper:", len(hidden), "| papers:", sorted(set(hidden.values())))
print("  speech errors:", [e.id for e in lib.random_errors if e.is_speech_error()])
print("  errors with <rare> in the name:", [e.id for e in lib.random_errors if "<rare>" in e.id])
print("  additional-error chances:", misc.get("hiddenAdditionalErrorPerc"), misc.get("speechAdditionalErrorPerc"))

patterns = C()
for entry in root.nodes:
    for _, node in T.tabtree.walk(entry):
        p = node.params or []
        if len(p) > 1 and p[0] == "=" and p[1] == "error":
            for token in p[2:]:
                patterns[token.rsplit(":", 1)[0] if ":" in token else token] += 1
            for child in node.nodes:
                patterns[" ".join(child.params[2:])] += 1
special = [p for p in patterns if any(re.search(r"[.*+?()\[\]{}|\\^$]", piece) for piece in p.split(" "))]
print("  distinct `= error` values in Travelers.txt:", len(patterns),
      "| containing pattern characters:", special)

days = [int(c) for c in table.col_ids[1:] if c.isdigit() and int(c) <= 31]
MASTERS = range(1, 13)


class Counting(E.Rand):
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


problems = []
draws = C()
outcome = C()
second_kind = C()
always = C()
recent_ok = recent_seen = 0
chosen = C()
for master in MASTERS:
    launch = Launch(master)
    for day_number in days:
        day = T.Day(table, day_number, launch.story_seed, FaceCycler(launch.face_cycler_seed))
        booth = Counting(day_seeds(day_number, launch.story_seed)["booth"])
        maker = E.ErrorMaker(booth, lib)
        context_maker = T.TravelerContext(root, world, day.facts)
        confiscation = table.cell(day_number, "CONFISCATE").replace("&amp;", "&") or None
        for _ in range(len(day.traveler_ids) + 12):
            spec = context_maker.make_spec(day.next_traveler_id(), day.traveler_rand)
            context = E.make_error_context(day.facts, spec, confiscation)
            value = spec.vars.get("error")
            candidates = lib.errors_for_context(value, context) if value is not None else []
            groups = {e.group for e in candidates}
            recent_before = list(maker.recent_groups)
            before = booth.count
            error = E.first_error(spec, context, maker)
            used = booth.count - before
            draws[(bool(candidates), used)] += 1
            if value is None:
                outcome["no error variable"] += 1
            elif not candidates:
                outcome["error variable, no candidate"] += 1
            else:
                outcome["error chosen"] += 1
                chosen[error.id] += 1
                if error not in candidates:
                    problems.append("chosen error is not a candidate")
                # The recent groups are dropped newest first while two or more remain.
                remaining = list(dict.fromkeys(e.group for e in candidates))
                for recent in recent_before:
                    if len(remaining) < 2:
                        break
                    if recent in remaining:
                        remaining.remove(recent)
                recent_seen += 1
                recent_ok += error.group in remaining
                if len(maker.recent_groups) > E.RECENT_GROUPS_MAX - 1:
                    problems.append("more than four groups remembered")
            before = booth.count
            second = E.additional_error(spec, error, context, maker, booth, misc)
            if error is not None:
                kind = ("hides a paper" if error.hidden_paper_id() else
                        "speech" if error.is_speech_error() else "other")
                rolled = booth.count - before
                second_kind[(kind, "second error" if second else
                             "rolled, none" if rolled else "no roll")] += 1
            for extra in lib.always_errors_for_context(context):
                always[extra.id] += 1

print("\n-- picking errors over %d days and %d master seeds --" % (len(days), len(MASTERS)))
print("  outcomes:", dict(outcome))
print("  draws used by the first pick (candidates?, draws):", dict(draws))
print("  chosen group allowed by the recent-groups rule: %d of %d" % (recent_ok, recent_seen))
print("  distinct errors chosen:", len(chosen), "of", len(lib.random_errors),
      "| most common:", chosen.most_common(4))
print("  after the first error (kind, what happened):", dict(sorted(second_kind.items())))
print("  always errors applied:", dict(always))
print("\nproblems:", sorted(set(problems)) or "none")
