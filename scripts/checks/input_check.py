"""Checks of the input handling (docs/input-handling.md) with
scripts/reference/inputs.py.

Usage: python -I input_check.py <reference dir> <assets dir>

1. The mouse on the screen quad to game pixels: the corners, and a pointer
   outside the window (held to the screen, but not its unclamped place).
2. Press, hold, release: down, just down, just up.
3. Double clicks: fast and close, too slow, too far, a third quick press.
4. Taking a pointer: who sees it on the next frames, with and without
   renewing the hold.
5. Blocked (masked) areas: the first asker blocks the ones after it, and
   the block ends with the frame.
6. A key masked until release (the pause on Escape), and all pointers
   masked until release (a held button does not count until let go).
7. The cursor: the first entity to set it wins; hiding it for one frame;
   where each cursor picture goes, against the pictures' sizes.
Needs Pillow for the picture sizes.
"""
import os
import sys

from PIL import Image

sys.path.insert(0, sys.argv[1])
import inputs as I  # noqa: E402

assets = sys.argv[2]
problems = []


def expect(name, got, want):
    ok = got == want
    print("   %-58s %s%s" % (name, got, "" if ok else "   (wanted %s)" % (want,)))
    if not ok:
        problems.append(name)


FRAME = 1 / 60.0
# Pointers 1 and 2 on desktop: never valid, so not down and "not from the
# mouse" (counted as touch points), which getPointerOver passes over.
UP = (False, (0.0, 0.0), True)


def frame(inp, t, down, pos, keys=None):
    inp.update(keys or [False] * 11, [(down, pos, False), UP, UP], t)
    return inp.pointers[0]


print("1. Mouse to game pixels")
expect("top left corner of the quad", I.host_to_game(-0.5, 0.5), (0.0, 0.0))
expect("just inside the bottom right corner", I.host_to_game(0.4999, -0.4999), (569.0, 319.0))
expect("the middle", I.host_to_game(0.0, 0.0), (285.0, 160.0))
inp = I.Input()
p = frame(inp, 0.0, False, (-30.0, 400.0))
expect("outside the window: held position", p.world, (0.0, 320.0))
expect("outside the window: unclamped position", p.unclamped, (-30.0, 400.0))

print("2. Press, hold, release")
inp = I.Input()
seq = []
for k, down in enumerate((False, True, True, False, False)):
    p = frame(inp, k * FRAME, down, (100.0, 100.0))
    seq.append((p.down, p.just_down, p.just_up))
expect("(down, just down, just up) per frame", seq,
       [(False, False, False), (True, True, False), (True, False, False),
        (False, False, True), (False, False, False)])

print("3. Double clicks")


def clicks(times_and_places):
    inp = I.Input()
    res = []
    t_end = max(t for t, _ in times_and_places) + 0.1
    frames = int(round(t_end / FRAME)) + 2
    presses = {int(round(t / FRAME)): pos for t, pos in times_and_places}
    for f in range(frames):
        pos = presses.get(f)
        p = frame(inp, f * FRAME, pos is not None, pos or (0.0, 0.0))
        if p.just_down:
            res.append(p.just_double)
    return res


expect("two presses 0.15 s apart, same place", clicks([(0.1, (50.0, 50.0)), (0.25, (50.0, 50.0))]), [False, True])
expect("two presses 0.25 s apart", clicks([(0.1, (50.0, 50.0)), (0.35, (50.0, 50.0))]), [False, False])
expect("two quick presses 3 pixels apart", clicks([(0.1, (50.0, 50.0)), (0.2, (53.0, 50.0))]), [False, False])
expect("two quick presses 1 pixel apart each way", clicks([(0.1, (50.0, 50.0)), (0.2, (51.0, 51.0))]), [False, True])
expect("three quick presses", clicks([(0.1, (50.0, 50.0)), (0.2, (50.0, 50.0)), (0.3, (50.0, 50.0))]),
       [False, True, True])

print("4. Taking a pointer")
A, B = "button A", "paper B"
rect = (0.0, 0.0, 200.0, 200.0)
inp = I.Input()
frame(inp, 0.0, False, (50.0, 50.0))
p = frame(inp, FRAME, True, (50.0, 50.0))
got = inp.pointer_just_down(A, rect)
expect("A takes the pointer on the press", got is p, True)
expect("B, asking after A in the same frame, sees it", inp.pointer_over(B, (0.0, 0.0, 570.0, 320.0)) is p, False)
p = frame(inp, 2 * FRAME, True, (300.0, 50.0))
expect("next frame, outside A's area: A still has it", inp.pointer_over(A, rect) is p, True)
expect("next frame: B does not see it", inp.pointer_over(B, (0.0, 0.0, 570.0, 320.0)) is None, True)
p = frame(inp, 3 * FRAME, True, (300.0, 50.0))
expect("two frames on, A did not renew: B sees it", inp.pointer_over(B, (0.0, 0.0, 570.0, 320.0)) is p, True)
inp = I.Input()
frame(inp, 0.0, False, (50.0, 50.0))
frame(inp, FRAME, True, (50.0, 50.0))
inp.pointer_just_down(A, rect)
held = []
for f in range(2, 6):
    p = frame(inp, f * FRAME, True, (50.0, 50.0))
    if inp.pointer_over(A, rect) is p:
        p.capture(A)
    held.append(p.capturing)
expect("A renews the hold every frame while held", held, [A, A, A, A])

print("5. Blocked areas")
inp = I.Input()
frame(inp, 0.0, False, (50.0, 50.0))
frame(inp, FRAME, False, (50.0, 50.0))
inp.pointer_just_down("top paper", (40.0, 40.0, 30.0, 30.0))
expect("the paper under it does not see the pointer", inp.pointer_over("lower paper", (0.0, 0.0, 100.0, 100.0)), None)
expect("the block's left and top edges count", inp.in_masked_area((40.0, 40.0)), True)
expect("its right and bottom edges do not", inp.in_masked_area((70.0, 50.0)), False)
p = frame(inp, 2 * FRAME, False, (50.0, 50.0))
expect("next frame the block is gone", inp.pointer_over("lower paper", (0.0, 0.0, 100.0, 100.0)) is p, True)

print("6. Masked until release")
ESC = 5
inp = I.Input()
esc = [False] * 11
esc[ESC] = True
inp.update(esc, [UP] * 3, 0.0)
first = inp.key_just_down(ESC)
inp.mask_key_until_release(ESC)
held = []
for f in range(1, 4):
    inp.update(esc, [UP] * 3, f * FRAME)
    held.append(inp.key_down(ESC))
inp.update([False] * 11, [UP] * 3, 4 * FRAME)
inp.update(esc, [UP] * 3, 5 * FRAME)
expect("Escape: just down, then masked while held", (first, held), (True, [False, False, False]))
expect("pressed again after letting go", inp.key_just_down(ESC), True)
inp = I.Input()
frame(inp, 0.0, True, (10.0, 10.0))
inp.mask_all_pointers_until_release()
seq = [frame(inp, f * FRAME, d, (10.0, 10.0)).just_down for f, d in enumerate((True, True, False, True), 1)]
expect("held button after masking: just down only after a new press", seq, [False, False, False, True])

print("7. Cursor")
inp = I.Input()
p = frame(inp, 0.0, False, (50.0, 50.0))
inp.pointer_just_down("top", (0.0, 0.0, 100.0, 100.0), "HAND")
p.set_cursor("ARROW")
expect("the first to set it wins", p.cursor, "HAND")
p = frame(inp, FRAME, False, (50.0, 50.0))
expect("cleared at the next frame", p.cursor, None)
inp.hide_pointers_for_one_frame()
hidden_now = inp.want_visible_cursor()
frame(inp, 2 * FRAME, False, (50.0, 50.0))
expect("hidden for the rest of the frame, back the next", (hidden_now, inp.want_visible_cursor()), (False, True))
for name, rel in I.CURSOR_PICTURES.items():
    w, h = Image.open(os.path.join(assets, rel)).size
    x, y = I.cursor_sprite_pos(name, (100.0, 100.0))
    print("   %-6s %s %dx%d, top left at (%g, %g) for the pointer at (100, 100)" % (name, rel, w, h, x, y))
    if (w, h) != (19, 26):
        problems.append("%s size" % rel)
for rel in ("assets/CursorScopeKill.png", "assets/CursorScopeTranq.png"):
    size = Image.open(os.path.join(assets, rel)).size
    x, y = I.cursor_sprite_pos("CUSTOM", (100.0, 100.0), size)
    print("   CUSTOM %s %dx%d, top left at (%g, %g)" % (rel, size[0], size[1], x, y))
    if (x, y) != (76.0, 76.0):
        problems.append("%s place" % rel)

print("problems:", "none" if not problems else "")
for p in problems:
    print("  ", p)
