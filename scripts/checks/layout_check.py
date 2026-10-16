"""Checks of the desktop layout values (docs/booth-layout.md).

Usage: python -I layout_check.py <reference dir> <emulator log> <dump.cs> <stringliteral.json>

1. Decodes the Layout printed by scripts/ghidra/EmulateLayout.java and
   compares every field with scripts/reference/layout.py.
2. Compares the run with the values read by hand from the instructions in
   earlier steps (border-view.md, screens.md parts 2 and 4, desk-pictures.md,
   page-layout.md), which the emulator did not see.
3. Prints how the booth's rectangles sit against each other.
"""
import json
import os
import subprocess
import sys
import tempfile

ref = sys.argv[1]
sys.path.insert(0, ref)
import layout as L  # noqa: E402

log, dump_cs, literals = sys.argv[2], sys.argv[3], sys.argv[4]
problems = []

# 1. A fresh decode against layout.py.
with tempfile.TemporaryDirectory() as tmp:
    out = os.path.join(tmp, "layout.json")
    subprocess.run([sys.executable, "-I", os.path.join(ref, "layout_dump.py"), log, dump_cs,
                    literals, out], check=True, stdout=subprocess.DEVNULL)
    decoded = json.load(open(out))


def norm(v):
    if isinstance(v, list):
        return tuple(norm(c) for c in v)
    if isinstance(v, dict):
        return {k: norm(c) for k, c in v.items()}
    if isinstance(v, float) and v.is_integer():
        return int(v)
    return v


compared = 0
for name, value in decoded.items():
    if name == "platform":
        continue
    compared += 1
    if norm(value) != norm(L.DESKTOP.get(name)):
        problems.append("%s: run %r, layout.py %r" % (name, value, L.DESKTOP.get(name)))
print("1. fields compared with layout.py:", compared)

# 2. Values read by hand from the instructions in earlier steps.
by_hand = {
    "border": (0, 0, 570, 103),               # border-view.md
    "borderScale": 1,
    "borderPersonHitSize": (8, 18),
    "borderSnipingTimescale": 1,
    "borderShowSnipingSurround": False,
    "borderCamRectL": None,
    "borderCamRectR": None,
    "borderOuterBoothButton": (146, 65),
    "tranqRifleButtonY": 113,
    "endlessScoreboardPos": (180, 2),
    "endlessScoreboardScrollWithBorder": True,
    "headerInEndless": False,
    "kPixelWidth": 570,
    "kPixelHeight": 320,
    "shape": "LANDSCAPE",
    "showPauseButton": False,                 # screens.md part 2
    "nightMessageWidth": 520,
    "titleShowVersion": True,
    "titleStackFooter": False,
    "titleLogoScale": 1,
    "titleLogoTop": 28,
    "titleMenuCenterY": 260,
    "menuItemPaddingY": 10,                   # screens.md part 4
    "settingsPadding": 4,
    "settingsTipsOnTop": False,
    "settingsButtonX": 180,
    "settingsButtonSize": (15, 15),
    "standardFooterButtonY": 290,
    "gameScreenHeaderY": 13,
    "layerWall": -3,                          # desk-pictures.md
    "layerMountedDeskItem": -2,
    "layerShutterShadow": -1,
    "layerStampDesk": 2,
    "layerFiler": 1,
    "touchTargetExpand": 0,                   # page-layout.md
}
matched = 0
for name, value in by_hand.items():
    if norm(decoded.get(name)) == norm(value):
        matched += 1
    else:
        problems.append("by hand %s = %r, run %r" % (name, value, decoded.get(name)))
print("2. values read by hand earlier that the run reproduces: %d of %d" % (matched, len(by_hand)))

# 3. The booth's rectangles, in the booth's coordinates.
D = L.DESKTOP
booth = D["booth"]
print("3. booth on screen", booth, "-> booth coordinates 0..%d x 0..%d" % (booth[2], booth[3]))
for name in ("wall", "counter", "console", "desk", "boothOuter", "boothOuterClamp",
             "boothInnerClamp", "boothInnerClip", "wallMountArea", "give"):
    r = D[name]
    print("   %-16s x %4d..%-4d y %4d..%-4d" % (name, r[0], r[0] + r[2], r[1], r[1] + r[3]))
if D["wall"][2] != D["desk"][0]:
    problems.append("the wall does not end where the desk starts")
if D["desk"][0] + D["desk"][2] != booth[2]:
    problems.append("the desk does not reach the booth's right edge")
if not (D["counter"][1] <= D["outerFloorMidY"] <= D["counter"][1] + D["counter"][3]):
    problems.append("outerFloorMidY is not on the counter")
for name, dp in D["dockPoints"].items():
    home = dp["home"]
    if not L.contains(D["boothOuter"], home[0], home[1]):
        problems.append("dock %s home outside boothOuter" % name)
print("   dock homes:", {k: v["home"] for k, v in D["dockPoints"].items()})

print("problems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
