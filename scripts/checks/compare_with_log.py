"""Compares the game's own log of a test-player run with the Python reference.

Usage: python -I compare_with_log.py <reference dir> <assets dir> <Player.log> <master seed>

<Player.log> is Unity's log of a run started with an auto.plan that has
`trace` and `seed <master seed>` (docs/comparing-with-the-game.md). The log
gives, per traveler: script entry, nationality, duration, purpose, starting
papers and errors. Days are counted from 1 in the order they appear.
"""
import re
import sys

sys.path.insert(0, sys.argv[1])
import booth as B
import speech as S
from cyclers import FaceCycler, NameCycler
from rand import Rand

log_path, master = sys.argv[3], int(sys.argv[4])
lines = open(log_path, encoding="utf-8", errors="replace").read().split("\n")

# ---------------------------------------------------------------- read the log
days = []                       # each: list of travelers
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith("[Game] Screen: day"):
        days.append([])
    elif line.startswith("[BoothEnv] New Traveler:") and days:
        head = lines[i + 1].split(" ")
        papers = lines[i + 2].split("PAPERS:", 1)[1].strip()
        traveler = {
            "entry": head[0], "nation": head[1], "duration": head[2].replace("months", ""), "purpose": head[3],
            "papers": [p for p in papers.split(", ") if p],
            "error": lines[i + 3].split("ERRORS:", 1)[1].strip(),
            "always": [], "additional": None, "said": [],
        }
        j = i + 4
        while j < len(lines) and not lines[j].startswith("[ErrorLib] Always Errors"):
            j += 1
        j += 2                                               # skip the "PaperIds:" line
        while j < len(lines) and lines[j].startswith("[ErrorLib]   "):
            name = lines[j][len("[ErrorLib]   "):].strip()
            if name != "No errors found":
                traveler["always"].append(name)
            j += 1
        days[-1].append(traveler)
    elif line.startswith("[BoothEnv] SAY ") and days and days[-1]:
        # a line actually spoken (the dumps of an error's lines are indented)
        days[-1][-1]["said"].append(line[len("[BoothEnv] SAY "):])
    elif line.startswith("[BoothEnv] Additional error: ") and days and days[-1]:
        days[-1][-1]["additional"] = line.split("Additional error: ", 1)[1].strip()
    i += 1
print("log: %d days, travelers per day: %s" % (len(days), [len(d) for d in days]))

# ---------------------------------------------------------------- run the reference
# A new game goes through the game's "load to screen" step, which draws a
# fresh story seed, so play uses the SECOND number of the story-seed generator.
generator = Rand(master + 73)
generator.next_int()
story_seed = generator.next_int()
print("master seed %d -> story seed in play %d (the second one drawn)" % (master, story_seed))
env = B.Env(sys.argv[2])
speeches = S.SpeechLib(open(sys.argv[2] + "/data/Speeches.txt", encoding="utf-8", newline="").read())
REPLAY_SPEECH = "--speech" in sys.argv        # experimental, see STATUS.md
face_cycler = FaceCycler(master)
name_cycler = NameCycler(env.names_m, env.names_f, master)

FIELDS = ["entry", "nation", "duration", "purpose", "papers", "error", "always", "additional"]
total = {f: [0, 0] for f in FIELDS}
first_miss = None
for day_number, logged in enumerate(days, start=1):
    booth = B.Booth(env, day_number, story_seed, face_cycler, name_cycler)
    print("\nday %d" % day_number)
    for index, seen in enumerate(logged):
        person = booth.make_new_traveler()
        v = person.spec.vars
        mine = {
            "entry": person.spec.id, "nation": v.get("nation"), "duration": str(v.get("duration")),
            "purpose": v.get("purpose"), "papers": list(person.spec.initial_papers),
            "error": person.error.id if person.error else "-",
            "always": [e.id for e in person.always_errors],
            "additional": person.additional_error.id if person.additional_error else None,
        }
        wrong = [f for f in FIELDS if mine[f] != seen[f]]
        for f in FIELDS:
            total[f][0] += mine[f] == seen[f]
            total[f][1] += 1
        if REPLAY_SPEECH:
            # Replay what the game said to this traveler: each stock line
            # draws from the booth's generator.
            for said in seen["said"]:
                S.get_speech(speeches, booth.rand, booth.value_text, said)
        if wrong and first_miss is None:
            first_miss = (day_number, index + 1)
        print("  %2d %-22s %-10s %-9s %-4s %-28s %s" % (
            index + 1, seen["entry"], seen["nation"], seen["purpose"], seen["duration"],
            ",".join(seen["papers"]) or "-", "ok" if not wrong else "DIFFERENT: " + "; ".join(
                "%s game=%r reference=%r" % (f, seen[f], mine[f]) for f in wrong)))

print("\nmatches by field:", {f: "%d of %d" % tuple(total[f]) for f in FIELDS})
print("first traveler with a difference:", "none" if first_miss is None else "day %d, traveler %d" % first_miss)
