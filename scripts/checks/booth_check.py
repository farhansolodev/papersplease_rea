"""Checks of scripts/reference/booth.py against the data files.

Usage: python -I booth_check.py <reference dir> <assets dir> [master seeds]

[master seeds] is how many master seeds the long part uses (default 4, about
one minute each; 0 runs only the short first part). Progress goes to the
error stream, one line per day.

Runs the whole of makeNewTraveler for the first travelers of every story day
and several master seeds, and checks on the results that a fact not marked
wrong shows the traveler's real details and that a fact marked wrong shows
something else.
"""
import collections
import sys

sys.path.insert(0, sys.argv[1])
import booth as B
import gdate
import person as P
from cyclers import FaceCycler, NameCycler
from seeds import Launch

C = collections.Counter
env = B.Env(sys.argv[2])
days = [int(c) for c in env.table.col_ids[1:] if c.isdigit() and int(c) <= 31]
MASTERS = range(1, 1 + (int(sys.argv[3]) if len(sys.argv) > 3 else 4))
EXTRA_TRAVELERS = 6

# Drawing a face (for the height) is most of the running time. Each sheet is
# read from disk once here; pieces are cut out as copies, so sharing is safe.
_load, _sheets = B.F.Image.load, {}
B.F.Image.load = staticmethod(lambda path: _sheets.get(path) or _sheets.setdefault(path, _load(path)))

problems = C()
generated = C()            # (fact name, valid?) -> times generated
empty_paths = C()          # paths that came out empty
op_kinds = C()
errors_applied = C()
draws = []
same_when_wrong = C()
travelers = 0
with_error = 0
criminals = C()

original = B.Booth.make_fact_value


def counted(self, path, valid, confusing=False):
    value = original(self, path, valid, confusing)
    name = path.split("/", 1)[1] if "/" in path else ""
    generated[(name.split("/")[0], "valid" if valid else "wrong")] += 1
    if value.text == "":
        empty_paths[path] += 1
    return value


B.Booth.make_fact_value = counted


def real_value(booth, t, path, fact):
    """What a fact shows when it is not wrong, for the kinds that can be told
    from the traveler alone. None for the others."""
    name = path.split("/", 1)[1]
    definition = env.lib.fact_defs.get(path)
    if name == "Name":
        return t.name.formatted(definition.format if definition else None)
    if name == "IdNumber":
        return t.id_number
    if name == "Nation":
        return t.nationality.upper()
    if name == "Gender":
        return "M" if t.male else "F"
    if name == "Height":
        return "%dcm" % t.height_cm
    if name == "Weight":
        return "%dkg" % t.weight
    if name == "Duration":
        return str(t.duration)
    if name == "Purpose":
        return t.purpose
    if name == "IssuingCity":
        return t.issuing_city
    if name == "District":
        return t.district
    if name == "BirthDate":
        return booth.format_date(gdate.after_years(booth.today, -t.meta.age))
    if name in ("Fingerprints", "Thumbprint"):
        return "".join(str(f) for f in t.fingerprints)
    if name in ("Exists", "Visible"):
        return "YES"
    if name == "Face" or name.startswith("Emblem"):
        return "VALID"
    if name == "UseDate":
        return booth.format_date(booth.today)
    return None


class Stuck(Exception):
    pass


def with_draw_limit(booth, limit, call):
    """Run call(); raise Stuck if it takes more than `limit` draws, which
    means a "redraw until different" loop that cannot end."""
    rand = booth.rand
    start, plain = rand.count, type(rand).random

    def limited():
        if rand.count - start > limit:
            raise Stuck()
        return plain(rand)

    rand.random = limited
    try:
        return call()
    finally:
        del rand.random


# Wrong values asked for directly, many times, on a day without and a day
# with the HARDER feature, to reach the branches that errors seldom or never
# take. The traveler is a foreigner: the game never asks for a wrong purpose
# or nation for an Arstotzkan native.
print("-- wrong values asked for directly, 300 times each --", flush=True)
harder_days = [d for d in days if "HARDER" in env.table.cell(d, "FEATURES")]
print("  HARDER is switched on in Days.csv on day:", harder_days or "none")
PATHS = ["Passport/IssuingCity", "Passport/IdNumber", "IdCard/District", "WorkPermit/Job",
         "DiplomaticAuth/Nation", "Bulletin/NowDate", "Passport/Name", "EntryPermit/Purpose",
         "EntryPermit/Duration", "IdSupplement/Description", "DiplomaticAuth/AccessNations",
         "VaccineCert/VaccineDrugs", "VaccineCert/VaccineDates", "WorkPermit/WorkEndDate"]
helper_calls = C()
for helper in ("make_typo", "make_alias"):
    def wrap(inner, helper=helper):
        def call(rand, word):
            helper_calls[helper] += 1
            return inner(rand, word)
        return call
    setattr(env.lang, helper, wrap(getattr(env.lang, helper)))
for day_number in ([days[0]] + harder_days[:1]):
    launch = Launch(1)
    booth = B.Booth(env, day_number, launch.story_seed, FaceCycler(launch.face_cycler_seed),
                    NameCycler(env.names_m, env.names_f, launch.name_cycler_seeds[0]))
    for _ in range(40):
        t = booth.make_new_traveler()
        if t.nationality != "Arstotzka" and t.purpose not in (None, "native"):
            break
    print("  day %d (HARDER %s), traveler %s %s of %s, purpose %s, duration %s:" % (
        day_number, booth.harder, t.first, t.last, t.nationality, t.purpose, t.duration), flush=True)
    for path in PATHS:
        helper_calls.clear()
        seen = C()
        try:
            for _ in range(300):
                seen[with_draw_limit(booth, 5000, lambda: original(booth, path, False)).text] += 1
        except Stuck:
            print("    %-28s STUCK: more than 5000 draws without a different value" % path, flush=True)
            continue
        except Exception as e:                                   # noqa: BLE001
            problems["direct %s on day %d: %r" % (path, day_number, e)] += 1
            continue
        real = original(booth, path, True).text
        print("    %-28s %3d different values, real value among them: %-5s typos %3d, aliases %3d" % (
            path, len(seen), real in seen, helper_calls["make_typo"], helper_calls["make_alias"]),
            flush=True)
print(flush=True)

for master in MASTERS:
    launch = Launch(master)
    face_cycler = FaceCycler(launch.face_cycler_seed)
    name_cycler = NameCycler(env.names_m, env.names_f, launch.name_cycler_seeds[0])
    for day_number in days:
        print("progress: master seed %d of %d, day %d of %d" % (master, len(MASTERS), day_number, len(days)),
              file=sys.stderr, flush=True)
        try:
            booth = B.Booth(env, day_number, launch.story_seed, face_cycler, name_cycler)
        except Exception as e:                                   # noqa: BLE001
            problems["day %d: booth not built: %r" % (day_number, e)] += 1
            continue
        for _ in range(len(booth.day.traveler_ids) + EXTRA_TRAVELERS):
            try:
                t = booth.make_new_traveler()
            except Exception as e:                               # noqa: BLE001
                problems["day %d: %s: %r" % (day_number, type(e).__name__, str(e)[:80])] += 1
                break
            travelers += 1
            draws.append(t.total_draws)
            with_error += bool(booth.applied_errors)
            if t.criminal_index is not None:
                criminals[t.criminal_index] += 1
            for error in booth.applied_errors:
                errors_applied[error.id.split("<")[0]] += 1
                for node in error.node.nodes:
                    op_kinds[node.params[0]] += 1
            desk = {info.id for info in booth.paper_infos.values()}
            for path, fact in booth.facts.items():
                paper = path.split("/")[0]
                if paper not in t.spec.initial_papers or paper not in desk or "/" not in path:
                    continue
                definition = env.lib.fact_defs.get(path)
                if definition is None or definition.val:        # a fixed value from Facts.xml
                    continue
                wrong = path in booth.invalid_paths
                real = real_value(booth, t, path, fact)
                name = path.split("/", 1)[1]
                if real is not None:
                    if not wrong and path not in booth.confusing_paths and fact.text != real:
                        problems["%s is not marked wrong but differs from the traveler" % name] += 1
                    if wrong and fact.text == real:
                        if path in booth.confusing_paths:
                            same_when_wrong[name + " (confusing: stays the same by design)"] += 1
                        else:
                            problems["%s is marked wrong but shows the real value" % name] += 1
                if name == "ExpirationDate" and fact.date is not None:
                    if wrong and not fact.date < booth.today:
                        problems["a wrong expiration date is not in the past"] += 1
                    if not wrong and not fact.date > booth.today:
                        problems["a valid expiration date is not in the future"] += 1
                if name == "AccessNations":
                    listed = fact.text.split(", ")
                    if ("ARSTOTZKA" in listed) != (not wrong):
                        problems["access nations: Arstotzka listed = %s when wrong = %s" % (
                            "ARSTOTZKA" in listed, wrong)] += 1
                    if not 2 <= len(listed) <= 4:
                        problems["access nations: %d names" % len(listed)] += 1
                if name == "VaccineDrugs":
                    drugs = fact.text.split("\n")
                    if len(drugs) != t.num_vaccines or len(set(drugs)) != len(drugs):
                        problems["vaccine list has the wrong length or a repeat"] += 1
                    if ("POLIO" in drugs) != (not wrong):
                        problems["vaccines: polio listed = %s when wrong = %s" % ("POLIO" in drugs, wrong)] += 1

if not travelers:
    print("problems:", dict(problems) or "none")
    sys.exit()
print("-- %d travelers over %d days and %d master seeds --" % (travelers, len(days), len(MASTERS)))
print("  with at least one error applied:", with_error)
print("  booth draws per traveler: fewest %d, most %d, average %.1f" % (
    min(draws), max(draws), sum(draws) / len(draws)))
print("  travelers who took a criminal's face, by criminal number:", dict(sorted(criminals.items())))
print("\n-- values generated, by fact name --")
names = sorted({name for name, _ in generated})
for name in names:
    print("  %-16s valid %6d   wrong %5d" % (name or "(the paper itself)",
                                            generated[(name, "valid")], generated[(name, "wrong")]))
print("\n-- paths that came out empty: %d distinct --" % len(empty_paths))
print("  ", ", ".join(sorted(empty_paths)))
print("\n-- errors applied: %d distinct --" % len(errors_applied))
print("  most common:", errors_applied.most_common(6))
print("  kinds of line at the top level of the applied errors:", dict(op_kinds))
print("  wrong but unchanged:", dict(same_when_wrong) or "none")
print("\nproblems:", dict(problems) or "none")
