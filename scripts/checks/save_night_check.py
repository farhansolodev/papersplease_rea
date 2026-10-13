"""Replay the night before each save of a real save folder with the night
model in scripts/reference/nights.py, and see whether it lands on the facts
the game saved.

A save does not record what the player did at night (how many travelers were
paid, which budget lines were ticked), so every possibility is tried and the
ones that reproduce the saved facts are counted.

Usage:
    python -I scripts/checks/save_night_check.py scripts/reference \
        <data dir> <save folder> dumps/il2cppdumper/stringliteral.json

Backs the "compared with a real save" notes in docs/night.md and
docs/save-format.md.
"""

import itertools
import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import nights as N      # noqa: E402
import savefile         # noqa: E402
import travspec as T    # noqa: E402

CORE = ("Night/Savings", "Night/FamilyAlive", "Night/wife", "Night/son",
        "Night/mil", "Night/uncle", "Night/niece")
OTHERS = ("Night/Flags", "Night/Profit", "Night/Calendar",
          "Night/NumEscapePassports", "Night/TokenIds", "Night/AttackResult")


def pairs(text):
    return dict(p.split("=", 1) for p in text.split(" ") if "=" in p)


def same(path, model, real):
    if path not in real:
        return path not in model or not model[path]
    if path not in model:
        return False
    if path in CORE[2:]:
        return pairs(model[path]) == pairs(real[path])
    return str(model[path]) == real[path]


def main() -> None:
    data, folder, literals_path = sys.argv[2:5]

    def read(name):
        with open(os.path.join(data, name), encoding="utf-8", newline="") as f:
            return f.read()

    texts = {m.group(1): m.group(2) for m in re.finditer(
        r'<item id="([^"]+)">\s*<t>(.*?)</t>', read("Text.xml"), re.S)}
    lib = N.NightLib(read("Nights.txt"))
    table, _, _ = T.load(data)

    key = savefile.load_key(literals_path)
    entries = savefile.read_folder(folder, key)
    nodes = savefile.parse_headers(entries["headers"])
    # Every save, in file order (a parent always comes before its children).
    chain = [n for n in nodes if n["id"] != "NEW"]
    print(f"saves: {len(chain)}")
    saved_facts = {}

    first = {"Game/Device": "desktop", "Game/Day": "1"}
    total_problems = 0
    for node in chain:
        real = dict(savefile.parse_facts(entries["save_" + node["id"]]))
        saved_facts[node["id"]] = real
        previous = saved_facts.get(node["parentId"], first)
        night = node["day"] - 1
        processed = (int(real.get("Game/Stat/NumProcessed", "0")) -
                     int(previous.get("Game/Stat/NumProcessed", "0")))
        event_ids = [e for e in T.split_and_trim(
            table.cell(night, "NIGHTEVENTS"), "\n") if e]

        tried = 0
        core_matches, full_matches = [], []
        for paid in range(processed + 1):
            probe = N.Family(lib, dict(previous), N.Summary(
                night, paid=paid, unpaid=processed - paid,
                night_event_ids=event_ids), texts)
            optional = [l.name for l in probe.budget.lines
                        if l.name in (texts["budget_food"],
                                      texts["budget_heat"])
                        or l.name in [probe.medicine_name(m)
                                      for m in probe.members]]
            for size in range(len(optional) + 1):
                for bought in itertools.combinations(optional, size):
                    tried += 1
                    facts = dict(previous)
                    family = N.Family(lib, facts, N.Summary(
                        night, paid=paid, unpaid=processed - paid,
                        night_event_ids=event_ids), texts)
                    for line in family.budget.lines:
                        if line.name in optional:
                            line.enabled = line.name in bought
                    family.apply_budget()
                    if all(same(p, facts, real) for p in CORE):
                        core_matches.append((paid, bought))
                        if all(same(p, facts, real) for p in OTHERS):
                            full_matches.append((paid, bought))
        print(f"\nsave {node['id'][:4]}..., night {night} ({processed} "
              f"travelers processed that day, night events "
              f"{event_ids or 'none'}):")
        print(f"  possibilities tried: {tried}")
        print(f"  reproduce savings, family count and every member: "
              f"{len(core_matches)}")
        print(f"  ... and also flags, profit, calendar, passports, tokens "
              f"and attack result: {len(full_matches)}")
        for paid, bought in core_matches:
            mark = "all facts" if (paid, bought) in full_matches \
                else "members and savings only"
            print(f"    {paid} paid, bought {list(bought) or 'nothing'} "
                  f"({mark})")
        if not full_matches:
            total_problems += 1
            print("  PROBLEM: no possibility reproduces the saved facts")

    print(f"\n{total_problems} problems")


if __name__ == "__main__":
    main()
