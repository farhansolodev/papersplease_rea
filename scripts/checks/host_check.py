"""Checks of the Unity side of drawing (docs/screen-output.md) with
scripts/reference/host.py.

Usage: python -I host_check.py <reference dir> <art dir>
(<art dir> = extracted\art; needs Pillow)

1. Drawing order: layers by number, visuals in added order, tiles in
   order, not-valid quads skipped.
2. Batching: slot 0 stays empty, a texture change opens a slot, 31
   changes or 1024 quads fill a mesh; the order is kept.
3. The texture table: added, re-sent when the change counter moves,
   kept, dropped after more than 10 unused frames.
4. The window size for common monitors; the full-screen choice.
5. The phantom cursor: its picture is the arrow's white edge, and it
   sits on the drawn arrow (the arrow's offset from input-handling.md).
6. The assumed pixel rule: where fractional quads land.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, sys.argv[1])
import host as H  # noqa: E402

art = sys.argv[2]
problems = []


def expect(name, got, want):
    ok = got == want
    print("   %-58s %s%s" % (name, got, "" if ok else "   (wanted %s)" % (want,)))
    if not ok:
        problems.append(name)


def quads(tag, n, image, valid=True):
    return [{"tag": "%s%d" % (tag, i), "image": image, "valid": valid} for i in range(n)]


print("1. Drawing order")
layers = {
    100: [quads("cursor", 1, "arrow")],
    5: [quads("paperA", 2, "pa"), quads("paperB", 1, "pb")],
    -3: [quads("bg", 1, "bg")],
    7: [quads("gone", 2, "x", valid=False) + quads("text", 2, "font")],
}
order = [q["tag"] for q in H.draw_order(layers)]
expect("order", order, ["bg0", "paperA0", "paperA1", "paperB0", "text0", "text1", "cursor0"])

print("2. Batching")
img = ["t%d" % i for i in range(40)]
m = H.batch([{"image": img[0]}, {"image": img[0]}, {"image": img[1]}])
expect("one mesh", len(m), 1)
expect("slot 0 empty, then one slot per texture run", m[0],
       [(None, 0, 0), (img[0], 0, 2), (img[1], 2, 1)])
m = H.batch([{"image": img[i]} for i in range(32)])
expect("32 texture changes: two meshes", len(m), 2)
expect("first mesh: slot 0 + 31 slots", len(m[0]), 32)
expect("second mesh starts with slot 0 again", m[1], [(None, 0, 0), (img[31], 0, 1)])
m = H.batch([{"image": "same"} for _ in range(1025)])
expect("1025 quads of one texture: two meshes", [len(x) for x in m], [2, 2])
expect("first mesh full at 1024", m[0][1], ("same", 0, 1024))
flat = []
for mesh in H.batch([{"image": img[i % 3]} for i in range(3000)]):
    for image, first, count in mesh:
        flat += [image] * count
expect("order kept across meshes (3000 quads)", flat == [img[i % 3] for i in range(3000)], True)

print("3. Texture table")
c = H.TextureCache()
c.evict(1)
expect("first use", c.get(7, 0, 1), "added")
expect("same counter", c.get(7, 0, 2), "kept")
expect("counter moved (drawn into)", c.get(7, 3, 3), "updated")
c.evict(13)
expect("still there 10 frames after last use", 7 in c.entries, True)
c.evict(14)
expect("dropped when last use < frame - 10", 7 in c.entries, False)
expect("made again on next use", c.get(7, 3, 14), "added")

print("4. Window and full screen")
for mon, want in [((1366, 768), (570, 320)), ((1600, 900), (570, 320)),
                  ((1680, 1050), (570, 320)), ((1711, 1080), (570, 320)),
                  ((1712, 962), (1140, 640)), ((1920, 1080), (1140, 640)),
                  ((1920, 1200), (1140, 640)), ((2560, 1440), (1140, 640)),
                  ((3440, 1440), (1140, 640)), ((3840, 2160), (2280, 1280))]:
    expect("windowed on %d x %d" % mon, H.window_size(*mon), want)
res = [(1280, 720, 50), (1280, 720, 60), (1920, 1080, 60), (2560, 1440, 144)]
expect("full screen: the monitor's own mode", H.fullscreen_mode(res), ((2560, 1440), 60, False))
expect("force720p", H.fullscreen_mode(res, force720p=True)[0], (1280, 720))
expect("force1080p missing: monitor's mode", H.fullscreen_mode(res[:2] + res[3:], force1080p=True)[0],
       (2560, 1440))

print("5. Phantom cursor")
assets = os.path.join(art, "assets")
ph = Image.open(os.path.join(assets, "CursorPhantom.png")).convert("RGBA")
ar = Image.open(os.path.join(assets, "CursorArrow.png")).convert("RGBA")
expect("same size as the arrow", ph.size, ar.size)
W, Hh = ph.size
opaque = {(x, y) for x in range(W) for y in range(Hh) if ph.getpixel((x, y))[3] == 255}
other = {(x, y) for x in range(W) for y in range(Hh) if 0 < ph.getpixel((x, y))[3] < 255}
white = {(x, y) for x in range(W) for y in range(Hh) if ar.getpixel((x, y)) == (255, 255, 255, 255)}
expect("opaque pixels", len(opaque), 39)
expect("no half-transparent pixels", len(other), 0)
expect("opaque pixels = the arrow's white pixels", opaque == white, True)
expect("their colours", sorted({ph.getpixel(p) for p in opaque}), [(85, 104, 85, 255)])
ARROW_OFFSET = (-1, -1)   # input-handling.md: the drawn arrow's top left from the pointer
for gx, gy in [(0, 0), (285, 160), (569, 319), (13, 200)]:
    tl = tuple(round(v, 6) for v in H.phantom_top_left(gx, gy, W, Hh))   # floats in the game too
    expect("at (%d, %d): on the drawn arrow" % (gx, gy), tl, (gx + ARROW_OFFSET[0], gy + ARROW_OFFSET[1]))

print("6. Assumed pixel rule (graphics card, not game code)")
expect("quad 10..30", H.covered_pixels(10, 30)[::19], [10, 29])
expect("quad 10.3..30.3", (H.covered_pixels(10.3, 30.3)[0], H.covered_pixels(10.3, 30.3)[-1]), (10, 29))
expect("quad 10.5..30.5", (H.covered_pixels(10.5, 30.5)[0], H.covered_pixels(10.5, 30.5)[-1]), (10, 29))
expect("quad 10.7..30.7", (H.covered_pixels(10.7, 30.7)[0], H.covered_pixels(10.7, 30.7)[-1]), (11, 30))
# A 20-pixel piece of a 64-wide picture drawn unscaled at 10.3: every
# pixel reads the texel one would get by drawing it at 10.
u0, u1 = 8 / 64.0, 28 / 64.0
got = [H.texel_at(i, 10.3, 30.3, u0, u1, 64) for i in H.covered_pixels(10.3, 30.3)]
expect("unscaled at 10.3 reads texels 8..27 in order", got, list(range(8, 28)))
got = [H.texel_at(i, 10.7, 30.7, u0, u1, 64) for i in H.covered_pixels(10.7, 30.7)]
expect("unscaled at 10.7 reads texels 8..27 in order", got, list(range(8, 28)))

print()
print("%d problems" % len(problems) + ("" if not problems else ": " + ", ".join(problems)))
