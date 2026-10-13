"""Check a real stash against what the code says about stashes.

Usage:
    python -I scripts/checks/stash_check.py scripts/reference <folder> \
        dumps/il2cppdumper/stringliteral.json <data folder>

<folder> holds a `stash.sav` written by the game (for example
`extracted/stash_sample`). <data folder> holds `Facts.xml` (for example
`extracted/art/assets/data`).

Backs docs/save-format.md, part 2. Every line printed is a finding; a line
starting with "PROBLEM" means the stash disagrees with the description.
"""

import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import hxserial  # noqa: E402
import savefile  # noqa: E402

# Field names from Il2CppDumper's dump.cs, class by class.
FIELDS = {
    "play.stash.StashedGame": {
        "stashVersion", "gameVersion", "screen", "platformKind", "day",
        "storyStateFacts", "dayScreen", "endId"},
    "play.stash.StashedDay": {
        "id", "facts", "numDetains", "numProcessedTravelersPaid",
        "numProcessedTravelersUnpaid", "attackResult", "numMadeTravelers",
        "hadBomber", "hadPoisoning", "bribeMoney", "tokenIds",
        "nightEventIds", "citations", "confiscatedPapers"},
    "play.stash.StashedDayScreen": {"booth", "border"},
    "play.stash.StashedBooth": {
        "engine", "paperStates", "shutterOpen", "criminalPosterPinned",
        "time"},
    "play.stash.StashedBoothEngine": {"numTravelers", "env"},
    "play.stash.StashedBoothEnv": {"facts", "dayPaperIds"},
    "play.stash.StashedBoothPaperState": {
        "id", "pos", "page", "outerImageAngle", "state", "placement"},
    "play.stash.StashedBorder": {"borderPan"},
}
STASHABLE_STATES = {"REVEALING", "NORMAL", "RETURNINGTODOCK"}
STASH_VERSION = 7

problems = 0


def problem(text: str) -> None:
    global problems
    problems += 1
    print("PROBLEM: " + text)


def check_fields(obj: dict) -> None:
    name = obj.get("__class")
    want = FIELDS.get(name)
    if want is None:
        problem(f"unexpected class {name}")
        return
    have = set(obj) - {"__class"}
    if have != want:
        problem(f"{name}: fields differ: missing {sorted(want - have)}, "
                f"extra {sorted(have - want)}")


def find_generator_state(value, path, found) -> None:
    """Collect any object of a random-generator class, anywhere."""
    if isinstance(value, dict):
        name = value.get("__class", "")
        if "Rand" in name:
            found.append(f"{path}: {name}")
        for key, item in value.items():
            find_generator_state(item, f"{path}.{key}", found)
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            find_generator_state(item, f"{path}[{i}]", found)


def staying_documents(data_folder: str) -> dict:
    """Document id -> its `stay` value, from Facts.xml."""
    with open(os.path.join(data_folder, "Facts.xml"), encoding="utf-8") as f:
        text = f.read()
    return dict(re.findall(r'<paper id="([^"]+)" stay="([^"]+)"', text))


def main() -> None:
    folder, literals_path, data_folder = sys.argv[2:5]
    key = savefile.load_key(literals_path)
    entries = savefile.read_folder(folder, key)
    text = entries.get("stash")
    if text is None:
        problem("no stash entry, or it does not decrypt")
        print("\n1 problem")
        return
    text = text.rstrip("\0")
    game, used = hxserial.unserialize(text)
    print(f"stash: {len(text)} characters, {used} read")
    if used != len(text):
        problem("text left over after the first value")

    # 1. The top object and what makes it valid (StashedGame.isValid).
    check_fields(game)
    kind = game["screen"][2]
    print(f"kind {kind}, layout {game['platformKind'][2]}, stash version "
          f"{game['stashVersion']}, game version {game['gameVersion']}")
    if game["stashVersion"] != STASH_VERSION:
        problem("stash version is not 7")
    if game["storyStateFacts"] is None:
        problem("no story facts")
    needs = {"DAY": ("day", "dayScreen"), "NIGHT": ("day",), "END": ("endId",)}
    for field in needs.get(kind, ()):
        if game[field] is None:
            problem(f"a {kind} stash without {field}")
    story = hxserial.fact_texts(game["storyStateFacts"])
    print(f"story facts: {len(story)}; Game/Device = "
          f"{story.get('Game/Device')}")

    # 2. No random generator state anywhere.
    found = []
    find_generator_state(game, "stash", found)
    print(f"random generator objects in the stash: {len(found)}")
    for line in found:
        problem("generator state at " + line)

    # 3. The day.
    day = game["day"]
    if day is not None:
        check_fields(day)
        print(f"day {day['id']}: travelers made {day['numMadeTravelers']}, "
              f"paid {day['numProcessedTravelersPaid']}, unpaid "
              f"{day['numProcessedTravelersUnpaid']}, detained "
              f"{day['numDetains']}; day facts "
              f"{len(hxserial.fact_texts(day['facts']))}")
        if not 1 <= day["id"] <= 31:
            problem("day number outside 1 to 31")
        if kind == "DAY" and day["numMadeTravelers"] < 1:
            problem("a day stash before any traveler was made")

    # 4. The day screen: booth, papers, border.
    screen = game["dayScreen"]
    if screen is None:
        print("no day screen in this stash")
    else:
        check_fields(screen)
        check_fields(screen["border"])
        print(f"border pan {screen['border']['borderPan']}")
        booth = screen["booth"]
        check_fields(booth)
        check_fields(booth["engine"])
        env = booth["engine"]["env"]
        check_fields(env)
        print(f"booth: clock {booth['time']:.3f}, shutter open "
              f"{booth['shutterOpen']}, poster pinned "
              f"{booth['criminalPosterPinned']}, travelers "
              f"{booth['engine']['numTravelers']}")

        whole = 0
        for state in booth["paperStates"]:
            check_fields(state)
            if state["state"][2] not in STASHABLE_STATES:
                problem(f"paper {state['id']} stashed in state "
                        f"{state['state'][2]}")
            pos = state["pos"]
            if pos["x"] == int(pos["x"]) and pos["y"] == int(pos["y"]):
                whole += 1
            print(f"  paper {state['id']}: {state['state'][2]}, "
                  f"{state['placement'][2]}, page {state['page']}, at "
                  f"({pos['x']}, {pos['y']})")
        print(f"papers: {len(booth['paperStates'])}, positions in whole "
              f"pixels: {whole}")
        if whole != len(booth["paperStates"]):
            problem("a paper position is not in whole pixels")

        # The booth's facts: only documents that stay, never Transcript.
        stay = staying_documents(data_folder)
        by_document = {}
        for path in hxserial.fact_texts(env["facts"]):
            document = path.split("/")[0]
            by_document[document] = by_document.get(document, 0) + 1
        print(f"booth facts by document: {by_document}")
        for document in by_document:
            if document == "Transcript":
                problem("a Transcript fact in the stash")
            if stay.get(document) not in ("day", "game"):
                problem(f"facts of {document}, which does not stay")
        print(f"day papers: {env['dayPaperIds']}")
        for paper_id in env["dayPaperIds"]:
            if stay.get(paper_id) != "day":
                problem(f"day paper {paper_id} has stay "
                        f"{stay.get(paper_id)!r}")

    print()
    print("0 problems" if problems == 0 else f"{problems} problem(s)")


if __name__ == "__main__":
    main()
