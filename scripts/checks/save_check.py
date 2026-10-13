"""Check a real save folder against what the code says about saves.

Usage:
    python -I scripts/checks/save_check.py scripts/reference <save folder> \
        dumps/il2cppdumper/stringliteral.json

Backs docs/save-format.md. Every line printed is a count; a line starting
with "PROBLEM" means the folder disagrees with the description.
"""

import os
import re
import sys

sys.path.insert(0, sys.argv[1])
import savefile  # noqa: E402

SETTINGS_KEYS = {"fullscreen", "nudity", "musicVolume", "soundVolume",
                 "easyMode", "dateFormatIndex", "endlessId",
                 "endlessUnlocked", "languageCode"}
ID_PATTERN = re.compile(r"^[A-Z0-9]{32}$")

problems = 0


def problem(text: str) -> None:
    global problems
    problems += 1
    print("PROBLEM: " + text)


def main() -> None:
    folder, literals_path = sys.argv[2:4]
    key = savefile.load_key(literals_path)
    entries = savefile.read_folder(folder, key)

    # 1. Every encrypted file decrypts, and encrypting the value again gives
    #    the file's exact text (cipher both ways, padding, upper-case hex).
    encrypted = [n for n in entries if n not in savefile.PLAIN_FILES]
    same = 0
    for name in encrypted:
        if entries[name] is None:
            problem(f"{name}: no {savefile.PREFIX} prefix after decrypting")
            continue
        with open(os.path.join(folder, name + ".sav"), encoding="utf-8") as f:
            content = f.read()
        if savefile.store_set(entries[name].rstrip("\0"), key) == content:
            same += 1
        else:
            problem(f"{name}: re-encrypting does not give the file's text")
    print(f"{len(encrypted)} encrypted files, {same} reproduced exactly "
          "by encrypting their decrypted value")
    highest = max((ord(c) for t in entries.values() if t for c in t),
                  default=0)
    print(f"highest character code in any decrypted text: {highest}")

    # 2. The tree of saves.
    if entries.get("headers") is None:
        problem("no headers entry")
        return
    nodes = savefile.parse_headers(entries["headers"])
    if nodes[0]["id"] != "NEW" or nodes[0]["depth"] != 0:
        problem("the first line of headers is not the root NEW")
    by_id = {}
    stack = []
    bad_parent = bad_id = bad_order = 0
    last_time_at_depth = {}
    for node in nodes:
        depth = node["depth"]
        del stack[depth:]
        if depth > len(stack):
            problem(f"{node['id']}: indented more than one level deeper")
        if stack:
            if node["parentId"] != stack[-1]["id"]:
                bad_parent += 1
            if not ID_PATTERN.match(node["id"]):
                bad_id += 1
        last = last_time_at_depth.get(depth)
        if stack and last is not None and last[0] is stack[-1] \
                and node["time"] < last[1]:
            bad_order += 1
        last_time_at_depth[depth] = (stack[-1] if stack else None,
                                     node["time"])
        stack.append(node)
        by_id[node["id"]] = node
    saves = [n for n in nodes if n["id"] != "NEW"]
    print(f"headers: {len(nodes)} lines, {len(saves)} saves, deepest level "
          f"{max(n['depth'] for n in nodes)}")
    print(f"  parent id differs from the line it hangs under: {bad_parent}")
    print(f"  ids that are not 32 characters of A-Z and 0-9: {bad_id}")
    print(f"  children not in time order: {bad_order}")
    if bad_parent or bad_id or bad_order:
        problem("headers tree")

    # 3. One file per header and one header per file.
    files = {n[5:] for n in entries if n.startswith("save_")}
    ids = {n["id"] for n in saves}
    print(f"save files: {len(files)}; headers without a file: "
          f"{len(ids - files)}; files without a header: {len(files - ids)}")
    if ids != files:
        problem("headers and save files do not match")

    # 4. The header repeats three facts of its save; the save remembers the
    #    save it was continued from.
    agree = parent_ok = 0
    for save_id in sorted(ids & files):
        facts = dict(savefile.parse_facts(entries["save_" + save_id]))
        node = by_id[save_id]
        got = (int(facts.get("Game/Day", "0")),
               int(facts.get("Night/Savings", "0")),
               int(facts.get("Night/FamilyAlive", "0")))
        if got == (node["day"], node["money"], node["family"]):
            agree += 1
        else:
            problem(f"{save_id}: header {node['day']}/{node['money']}/"
                    f"{node['family']} but facts say {got}")
        file_parent = facts.get("Save/ParentId", "NEW")
        file_parent_day = int(facts.get("Save/ParentDay", "1"))
        expected = file_parent if node["day"] > file_parent_day else "NEW"
        if node["parentId"] == expected and (
                expected == "NEW"
                or by_id[expected]["day"] == file_parent_day):
            parent_ok += 1
        else:
            problem(f"{save_id}: parent {node['parentId']}, file says "
                    f"{file_parent} (day {file_parent_day})")
        if facts.get("Game/Device") not in ("desktop", "tablet", "phone",
                                            "unknown"):
            problem(f"{save_id}: Game/Device is {facts.get('Game/Device')}")
    print(f"  header day, money and family equal the save's facts: {agree}")
    print(f"  header parent follows the save's Save/ParentId rule: "
          f"{parent_ok}")

    # 5. Settings, statistics, names.
    if entries.get("settings"):
        members = savefile.parse_members(entries["settings"])
        unknown = [k for k, _ in members if k not in SETTINGS_KEYS]
        print(f"settings: {len(members)} entries, "
              f"{len(unknown)} with a name the code does not write")
        if unknown:
            problem(f"settings entries {unknown}")
    if entries.get("stats"):
        members = savefile.parse_members(entries["stats"])
        not_int = [k for k, v in members if not re.match(r"^-?\d+$", v)]
        print(f"stats: {len(members)} entries, {len(not_int)} not whole "
              "numbers")
    if entries.get("names"):
        lines = entries["names"].rstrip("\0").split("\n")
        parts = [line.split(":") for line in lines]
        shape_ok = len(parts) == 2 and all(len(p) == 3 for p in parts)
        print(f"names: {len(lines)} lines, shape seed:position:reshuffles "
              f"{'yes' if shape_ok else 'NO'}")
        if shape_ok:
            print(f"  second seed is the first plus one: "
                  f"{int(parts[1][0]) == int(parts[0][0]) + 1}; names taken: "
                  f"{parts[0][1]} + {parts[1][1]}")
        else:
            problem("names entry has another shape")
    print(f"stash entry present: {'stash' in entries}")
    print(f"\n{problems} problems")


if __name__ == "__main__":
    main()
