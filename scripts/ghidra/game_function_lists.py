"""Write address lists of the game's own functions, one file per part of the game.

Usage: python -I game_function_lists.py <script.json> <output folder>

Each list is a text file of 0xADDRESS lines that DecompileFunctions.java reads
with a selector of the form @<file>. The functions come from Il2CppDumper's
script.json. Only the game's own classes are listed: the namespaces play, app,
data and test, and the game classes that have no namespace. The Haxe and .NET
runtime, Unity and Steamworks are left out.

Also left out, on purpose: the platform's social service (achievements and
leaderboards) and the Steam wrappers. They are outside this project's scope
(single-player and offline only).

An address shared by several functions is listed once, in the first part that
names it (parts in alphabetical order).
"""
import collections
import json
import os
import sys

IMAGE_BASE = 0x180000000

# Classes without a namespace that belong to the game. The other classes
# without a namespace are the Haxe standard library (Array, Std, Xml, ...).
TOP_LEVEL_GAME = (
    "Game", "GameParams", "HostUnity", "InputWrapper", "Layout", "Db", "Res",
    "ScreenChange", "Aspect", "Asset", "BoothLayout", "ConsoleKind", "Shape",
    "Main", "EntryPoint__Main", "QuadBatcher", "Locale", "Trace", "Unbug",
    "Version", "Vibration",
)

EXCLUDED_PREFIXES = ("app.plat.PlatformSocial", "SocialWrapper", "SteamManager")

# Longest match wins.
PARTS = (
    ("play.day.booth", "play_day_booth"),
    ("play.day.border", "play_day_border"),
    ("play.day", "play_day"),
    ("play.night", "play_night"),
    ("play.screen", "play_screen"),
    ("play.ui", "play_ui"),
    ("play", "play_misc"),
    ("app.ent", "app_ent"),
    ("app.vis", "app_vis"),
    ("app.plat", "app_plat"),
    ("app.aud", "app_aud"),
    ("app", "app_misc"),
    ("data", "data"),
    ("test", "test"),
)


def part_of(class_name):
    """The list a class goes into, or None if it is not a game class."""
    if class_name.startswith(EXCLUDED_PREFIXES):
        return None
    # "Game_createStater_188__Fun" and "HostUnity.CachedTexture" belong to
    # Game and HostUnity.
    root = class_name.split(".")[0]
    if root in TOP_LEVEL_GAME or root.split("_")[0] in TOP_LEVEL_GAME:
        return "top"
    best = None
    for namespace, part in PARTS:
        if class_name == namespace or class_name.startswith(namespace + "."):
            if best is None or len(namespace) > len(best[0]):
                best = (namespace, part)
    return best[1] if best else None


def main():
    methods = json.load(open(sys.argv[1], encoding="utf-8"))["ScriptMethod"]
    out_dir = sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)

    by_part = collections.defaultdict(set)
    excluded = collections.Counter()
    for method in methods:
        class_name = method["Name"].split("$$")[0]
        if class_name.startswith(EXCLUDED_PREFIXES):
            excluded[class_name] += 1
            continue
        part = part_of(class_name)
        if part is not None:
            by_part[part].add(method["Address"])

    seen = set()
    total = 0
    for part in sorted(by_part):
        addresses = sorted(by_part[part] - seen)
        seen.update(addresses)
        total += len(addresses)
        with open(os.path.join(out_dir, part + ".txt"), "w", encoding="utf-8") as out:
            for address in addresses:
                out.write("0x%x\n" % (IMAGE_BASE + address))
        print("%5d  %s" % (len(addresses), part))
    print("%5d  total" % total)
    print("left out on purpose: %d functions in %d classes (%s)" % (
        sum(excluded.values()), len(excluded), ", ".join(sorted(excluded))))


main()
