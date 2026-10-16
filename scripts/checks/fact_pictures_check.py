"""Checks of the fact pictures (docs/fact-pictures.md) against Papers.xml,
Facts.xml, the pictures and scripts/reference/factpics.py.

Usage: python -I fact_pictures_check.py <reference dir> <assets dir> <stringliteral.json>

1. Every picture mark showing a fact, sorted into the branch of
   BoothEnv.getImage that serves it.
2. For the branch "a picture file named by the value": every value the fact
   can hold (Facts.xml, or set by the code) names an existing picture.
3. Sizes: the document photo at each scale used, the scaled pictures, the
   fingerprint sheets, the seal sheets, the body pictures.
4. The document photo's black background never shows (sample faces, every
   scale used, every vertical shift, mirrored or not).
5. The search photo's contraband marks sit where the cut piece belongs on
   the body.
Needs Pillow.
"""
import collections
import json
import math
import os
import sys

sys.path.insert(0, sys.argv[1])
import factlib
import factpics as FP
import faces as F
import pages as P
from rand import Rand

assets = sys.argv[2]
code_strings = {e["value"] for e in json.load(open(sys.argv[3], encoding="utf-8"))}
data = os.path.join(assets, "data")
papers = P.load(assets)
lib = factlib.FactLib(open(os.path.join(data, "Facts.xml"), encoding="utf-8").read())
problems = []
C = collections.Counter

# Values the code writes into facts shown as pictures (found by searching the
# decompile for the fact paths; docs/fact-pictures.md, "Where the values come from").
CODE_VALUES = {
    "Bulletin/PagesNote": ["BulletinPagesNote.png"],            # BoothEnv.addBulletinForDay
    "Bulletin/Emblem0": ["BulletinEmblem"],                     # same, last notice page
    "Bulletin/Emblem1": ["BulletinEmblem"],
    "Transcript/NextPage0": ["TranscriptNext.png"],             # BoothEnv.applyOp
    "Transcript/NextPage1": ["TranscriptNext.png"],
    "Rules/Upgrade0": ["RulesUpgrade0.png", "RulesUpgrade4.png", "RulesUpgrade2.png"],  # BoothEnv constructor,
    "Rules/Upgrade1": ["RulesUpgrade1.png", "RulesUpgrade2.png"],                       # by upgrade set
    "Rules/Upgrade2": ["RulesUpgrade2.png"],
    "Rules/Upgrade3": ["RulesUpgrade3.png"],
}


def branch(paper_id, fact):
    """BoothEnv.getImage's order of tests (with a traveler present)."""
    if fact == "Face":
        return "document photo"
    if paper_id == "Photo":
        if fact in ("HeadFront", "HeadBack"):
            return "search photo head"
        if fact in ("BodyFront", "BodyBack"):
            return "search photo body"
        if fact in ("ContrabandBack", "ContrabandBackLegL", "ContrabandBackLegR"):
            return "contraband"
        return "nothing"
    if fact == "Fingerprints":
        return "fingerprints"
    if fact == "Thumbprint":
        return "thumbprint"
    if fact.startswith("Criminal"):
        return "criminal photo"
    if fact in ("SealsMoa", "SealsMol"):
        return "valid seals sheet"
    return "by value"


print("-- 1. picture marks showing a fact, by branch --")
marks = collections.defaultdict(list)        # (paper, fact) -> [mark]
for paper in papers:
    for page in paper.pages:
        for mark in page.marks:
            if mark.type == "IMAGE" and mark.image.startswith("$"):
                marks[(paper.id, mark.image[1:])].append(mark)
by_branch = collections.defaultdict(list)
for (paper_id, fact), ms in sorted(marks.items()):
    by_branch[branch(paper_id, fact)].append((paper_id, fact, len(ms)))
for name, items in by_branch.items():
    print("  %-20s %2d facts, %2d marks: %s" % (name, len(items), sum(n for _, _, n in items),
          ", ".join("%s/%s" % (p, f) for p, f, _ in items)))
if by_branch.get("nothing"):
    problems.append("a Photo fact getImage gives nothing for: %s" % by_branch["nothing"])
photos = [(p, f) for p, f, _ in by_branch["document photo"]]
print("  document photos mirrored and recoloured (paper id is not 'Passport'): %s" %
      sorted({p for p, _ in photos if p != "Passport"}))

print("\n-- 2. values of the facts shown by their value --")
missing = []
for paper_id, fact, _ in by_branch["by value"]:
    path = paper_id + "/" + fact
    values = []
    definition = lib.fact_defs.get(path)
    if definition is not None and definition.val:
        values.append(("Facts.xml", definition.val))
    for v in CODE_VALUES.get(path, []):
        values.append(("code", v))
        if v not in code_strings:
            problems.append("%s: the code value %s is not among the code's strings" % (path, v))
    if not values:
        missing.append(path)
        continue
    for source, value in values:
        if value == "BulletinEmblem":
            kind = "bulletin seal"
        else:
            ok = os.path.exists(os.path.join(assets, "papers", value))
            kind = "file found" if ok else "FILE MISSING"
            if not ok:
                problems.append("%s: %s names a missing picture" % (path, value))
        print("  %-28s %-9s %-28s %s" % (path, source, value, kind))
if missing:
    print("  no value found for: %s" % missing)
    problems.append("no value for %s" % missing)
print("  Facts.xml says of SealsMoa and SealsMol: their val is empty, under the comment 'Moved to code'")

print("\n-- 3. sizes --")
scales = C()
for (paper_id, fact), ms in marks.items():
    for m in ms:
        scales[(branch(paper_id, fact), m.scale)] += 1
for (name, scale), n in sorted(scales.items()):
    if name == "document photo":
        w, h = FP.math_round(FP.DOC_W * scale), FP.math_round(FP.DOC_H * scale)
        print("  document photo at %.2f: %d x %d (%d marks; missing fact: %d x %d red)" % (
            scale, w, h, n, int(math.floor(FP.DOC_W * scale)), int(math.floor(FP.DOC_H * scale))))
    elif name == "criminal photo":
        im = FP.transformed(F.Image(FP.DOC_W, FP.DOC_H, 0xFFFFFFFF), 0.0, scale)
        print("  criminal photo: 80 x 96 drawn at scale 1, then scaled %.2f: %d x %d (%d marks)" % (
            scale, im.width, im.height, n))
    elif abs(scale - 1.0) > FP.SCALE_EPSILON:
        print("  %s scaled %.2f: %d marks" % (name, scale, n))
for nation in [n for n, _ in lib.nations]:
    cover = FP.load(os.path.join(assets, "papers", "PassportOuter%s.png" % nation))
    half = FP.transformed(cover, 0.0, 0.5)
    print("  Rules/%s-Passport0: %d x %d -> %d x %d" % (nation, cover.width, cover.height,
                                                       half.width, half.height))
sheet = FP.load(os.path.join(assets, "FingerSworls.png"))
blank = FP.load(os.path.join(assets, "FingerSworlBlank.png"))
kinds = C(sheet.px)
print("  FingerSworls.png %d x %d (%d columns x %d rows of 32), colours %s" % (
    sheet.width, sheet.height, sheet.width // 32, sheet.height // 32,
    {"%08X" % k: v for k, v in kinds.items()}))
print("  FingerSworlBlank.png %d x %d" % (blank.width, blank.height))
if (sheet.width, sheet.height) != (96, 320):
    problems.append("FingerSworls.png is not 96 x 320")
alpha_one = C()
r = Rand(7)
for trial in range(200):
    fingers = [int(r.random() * 10) for _ in range(5)]
    im = FP.fingerprint_image(assets, fingers, r, 0x202020)
    alpha_one.update(p >> 24 for p in im.px)
total = sum(alpha_one.values())
print("  fingerprint pictures (200 random codes): alpha 0 %.1f%%, alpha 1 %.1f%%, alpha 255 %.1f%%, other %d" % (
    100.0 * alpha_one[0] / total, 100.0 * alpha_one[1] / total, 100.0 * alpha_one[255] / total,
    total - alpha_one[0] - alpha_one[1] - alpha_one[255]))
emblems = FP.Emblems(assets)
for emblem_id in ("MinistryOfAdmission", "MinistryOfLabor"):
    s = emblems.first(emblem_id)
    im = FP.valid_seals_image(emblems, emblem_id, 0xE4E6BD)
    rows = (s["valid"] + 1) // 2
    shifts = [int(math.floor(i * 0.5)) * int(s["size"][1]) + int(math.floor(i / rows)) for i in range(s["valid"])]
    print("  %s: %d valid, sheet picture %d x %d, seal tops %s" % (
        emblem_id, s["valid"], im.width, im.height, shifts))
    grid = emblems.grid(s)
    cw, ch = (int(v) for v in s["size"])
    columns = grid.width // cw
    for i in range(s["valid"]):
        top = shifts[i]
        lost = top + ch - im.height
        if lost > 0:
            cx, cy = i % columns * cw, i // columns * ch
            opaque = sum(1 for yy in range(ch - lost, ch) for xx in range(cw)
                         if grid.px[(cy + yy) * grid.width + cx + xx] >> 24)
            print("    seal %d loses its bottom %d row(s): %d non-transparent pixels there" % (i, lost, opaque))
for body in ("F0", "F1", "F2", "M0", "M1", "M2"):
    for suffix in ("", "c"):
        im = FP.load(os.path.join(assets, "faces", "Body%s%s.png" % (body, suffix)))
        if (im.width, im.height) != (200, 200):
            problems.append("Body%s%s.png is %d x %d" % (body, suffix, im.width, im.height))
print("  body pictures: all 200 x 200 (cut to 100 x 160)" if not any("Body" in p for p in problems) else "")
palette = FP.load(os.path.join(assets, "FacePalette.png"))
print("  FacePalette.png %d x %d: rows 7 and 8 (photo front, back) at y 70, 80: %s" % (
    palette.width, palette.height, "present" if palette.height > 80 else "MISSING"))

print("\n-- 4. the document photo's black background --")
flib = F.FaceLib(os.path.join(data, "Faces.xml"), os.path.join(assets, "FacePalette.png"))
faces_dir = os.path.join(assets, "faces")
doc_scales = sorted({s for (name, s) in scales if name in ("document photo",)} | {1.0})


class Fixed:
    def __init__(self, value):
        self.value = value

    def random(self):
        return self.value


shown = 0
tried = 0
r = Rand(11)
for k in range(12):
    gender = "M" if k % 2 == 0 else "F"
    spec = "%s-%d-%d-%d-%d-0-%d" % (gender, int(r.random() * 20), int(r.random() * 20),
                                    int(r.random() * 20), int(r.random() * 20), k // 2 % 2)
    face = F.Face(faces_dir, flib, F.FaceSpec(spec), for_doc=True)
    for scale in doc_scales:
        for value in (0.0, 0.3, 0.6, 1.0):       # shifts 3, 4, 5, 6
            for flip in (False, True):
                im = FP.doc_image(face, Fixed(value), scale, flip, False)
                tried += 1
                if 0xFF000000 in im.px:
                    shown += 1
print("  %d pictures (12 faces, scales %s, shifts 3 to 6, mirrored or not): black shows in %d" % (
    tried, doc_scales, shown))
if shown:
    problems.append("the document photo's black background shows in %d pictures" % shown)

print("\n-- 5. contraband marks against the body mark --")
bodies = FP.Bodies(assets)
photo = next(p for p in papers if p.id == "Photo")
back = next(pg for pg in photo.pages if pg.id == "back")
body_pos = next(m.pos for m in back.marks if m.image == "$BodyBack")
for fact, loc in (("ContrabandBack", "back"), ("ContrabandBackLegL", "legl"), ("ContrabandBackLegR", "legr")):
    pos = next(m.pos for m in back.marks if m.image == "$" + fact)
    rect = bodies.locs[loc]
    expect = (body_pos[0] + rect[0], body_pos[1] + rect[1])
    print("  %-20s mark at %s, body at %s + loc %s at %s: %s" % (
        fact, pos, body_pos, loc, tuple(rect[:2]), "same" if pos == expect else "DIFFERENT"))
    if pos != expect:
        problems.append("%s mark is not at the body position plus its loc" % fact)
    for entry in bodies.contras:
        if entry.get("loc") == loc:
            for b in ("F0", "F1", "F2", "M0", "M1", "M2"):
                piece, paste_pos = bodies.piece(entry, b)
                if paste_pos != tuple(rect[:2]) or (piece.width, piece.height) != (int(rect[2]), int(rect[3])):
                    problems.append("%s on %s: piece %dx%d at %s" % (entry.get("file"), b, piece.width,
                                                                      piece.height, paste_pos))

print("\nproblems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
