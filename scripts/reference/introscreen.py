"""The intro screen of milestone 3c (docs/milestone-3.md): the page player
(play.screen.Intro) with the five pages of Intro.xml, frame by frame, at
1/60 s a frame. Written from the code (docs/screens.md part 5, read again in
full for this step) before the Rust, and drawn with the same quad rules as
fontpage.py.

    python -I scripts/reference/introscreen.py <assets dir> <out dir>

for example `extracted/art/assets` and `extracted/previews/m3c` (gitignored).
It plays one fixed run (SCRIPT below: when NEXT is clicked and when a press
hurries a page) and writes:

- timeline.json: for every frame, the page, the state, the wipe's cut, how
  many letters of the caption are shown, NEXT shown or not; the frames on
  which `text-reveal` plays; the frame on which the last NEXT ends the pages;
- <name>.rgba for the frames in SNAPSHOTS (570 x 320 x 4 bytes, alpha 255),
  each also as a PNG and, enlarged 3 times, as _x3.png to look at.

port/core/tests/intro.rs drives the port's game through the same run with
real mouse presses and compares both, byte for byte and frame for frame.

What the code does, as read (Intro constructor 0x1808fae90, its ENTER, STEP
and EXIT functions Intro_85 0x180483eb0, Intro_132 0x1804837c0 and
Intro_146 0x180483c50, react 0x1808fcde0, endFlipNow, nexButton_onClick,
update; RevealTextEnt set_text, stepReveal, revealAll; app.Stater go and
step, app.State enter, exit and step; Tween.step, Tweener.timer;
Sprite.rebuild and width; Quad.make; Text.buildTiles' built letters):

- Frames. A screen built by a screen change is built and then updated and
  asked for input in the same frame (docs/milestone-3.md, 3b). Here frame 1
  builds the screen, then every frame runs the page timers, the state
  machine's step, then NEXT's input, then the player's own input.
- Two states, no blend times. `flipping`: ENTER shows the page, STEP runs
  the wipe and, after 1 s, the typing; EXIT finishes the page. `idle`:
  nothing. NEXT is hidden in `flipping` and shown in `idle` (the states'
  targets, applied on entering). The state's clock gets the frame's time
  before STEP runs, so STEP first sees 1/60.
- ENTER (show a page): the caption emptied, given its colour (white
  0xffffff when the page has none; note: alpha 0) and its text; placed at
  x = floor(285 - width / 2), y = floor(227 - height / 2); then
  stepReveal once, with this frame's time (it counts the countdown down
  and hides every letter). The picture `assets/intro/<image>` goes into the
  NEXT holder, at x = floor(285 - its width / 2), y 32. A page `sound` is
  set to play 2 s later (Tweener.timer). Pages with `when`: not supported
  here (the intro has none; endings come later).
- STEP: t = the state's clock held to 0..1; the cut is
  Math.round(right - width x t) of the CURRENT holder (right = its x plus
  width); the current picture shows left of the cut, the next one right of
  it (clip rectangles in the screen's coordinates); then, once the clock
  is past 1 s (strictly), stepReveal; when it has no letter left to show,
  `idle`.
- The current holder on the first page has no picture: Sprite.rebuild with
  no picture makes its size 0 x 0 and its x is 0, so the cut is 0 and the
  first picture shows whole at once (settles an open note of screens.md
  part 5).
- EXIT: the next holder's picture becomes the current one's, at
  x = floor(285 - width / 2), unclipped; the next holder is hidden;
  revealAll shows every letter. revealAll plays `text-reveal` only when
  `revealIndex < revealCount`; nothing in the game sets `revealCount` (its
  name appears only in RevealTextEnt's own field helpers), so it is 0 and
  revealAll never plays it.
- stepReveal: nothing (answer: no) when every built letter is shown;
  otherwise the countdown loses the frame's time and, while it is below 0,
  the next letter is shown (`text-reveal` plays when its index is a
  multiple of 3) and the countdown gains 0.5 s after `.` or `。`, 0.25 s
  after `,` or `、`, 0.04 s after any other letter; then every letter's
  alpha is set, 1 if shown, else 0 (answer: yes).
- Built letters: each character of the laid-out lines that the font has,
  spaces included (they have no picture); a character the font lacks has
  none.
- NEXT (Button, PushButton.png's top 19 rows, `menu_next` in ui_large,
  colour 0x556855): x = floor(285 - 129 / 2) = 220, y = 290. A click moves
  to the next page and enters `flipping`; after the last page it ends the
  pages (the intro screen then fades to the day-1 newspaper; the port, for
  now, to the title).
- Hurrying (react): only with hurrying allowed (the intro) and from the
  second page on; a pointer pressed anywhere on the screen this frame, not
  taken by NEXT, ends a `flipping` at once (endFlipNow: `idle`, so EXIT).
- Drawing order: the screen's black fill, the current holder, the next
  holder, the caption's letters, NEXT.
"""

import json
import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fontpage  # noqa: E402
import fonts  # noqa: E402
import text as textmod  # noqa: E402
import titlescreen  # noqa: E402
from PIL import Image  # noqa: E402

W, H = fontpage.W, fontpage.H
DT = 1.0 / 60.0

# Desktop values (docs/screens.md part 5, "Layout").
IMAGE_Y = 32
TEXT_CENTER_Y = 227
TEXT_WIDTH = 380                # introTextWidth
FOOTER_Y = 290                  # standardFooterButtonY
WIPE = 1.0                      # the wipe's length, seconds
SOUND_DELAY = 2.0               # a page's sound, seconds after it starts
PUSH_BAND = 19
GREEN = 0xFF556855

# The run (run() below), frames counted from 1: on each page, 20 frames
# after it has come to rest, NEXT is clicked ("next": pressed on the frame
# before, let go on this one, so it clicks in this frame's input). The third
# page is hurried 10 frames after it began (mid-wipe) and the fourth 70
# frames after (mid-typing): "hurry", a press on that frame on NEXT's spot,
# let go on the next frame (which must not click NEXT).
SNAPSHOTS = ["page1_rest", "page2_wipe", "page2_typing", "page2_rest", "page3_hurried", "page4_rest",
             "page5_rest"]


def math_round(x):
    """Haxe Math.round as compiled (port/core/src/num.rs)."""
    i = int(x)
    d = x - i
    if d >= 1.0 or -1.0 >= d:
        return i
    if d >= 0.5:
        return i + 1
    if -0.5 > d:
        return i - 1
    return i


def lerp_scale(x, in0, in1, out0, out1):
    x = max(min(x, in1), in0)
    return (x - in0) / (in1 - in0) * (out1 - out0) + out0


def built_letters(font, string, fixed_width, multi_line):
    """Text.buildTiles' built letters: (character, index of its tile or None)
    for every character of the laid-out lines that the font has."""
    if not string:
        return []
    lines, _, _, _ = font.split(string, fixed_width, multi_line)
    out, tile = [], 0
    for line, _ in lines:
        for ch in line:
            letter = font.letters.get(ord(ch))
            if letter is None:
                if ord(ch) != textmod.SPACE:
                    tile += 1                   # a box: a tile, but no built letter
                continue
            if ord(ch) == textmod.SPACE:
                out.append((ch, None))
            else:
                out.append((ch, tile))
                tile += 1
    return out


class Caption:
    """play.ui.RevealTextEnt with its label (title_tall, fixed width 380,
    several lines)."""

    def __init__(self, font):
        self.font = font
        self.text = ""
        self.color = 0
        self.x = self.y = 0
        self.index = 0
        self.countdown = 0.0
        self.alpha = []

    def _rebuild(self):
        self.letters = built_letters(self.font, self.text, TEXT_WIDTH, True)
        a = (self.color >> 24) / 255.0
        self.alpha = [a] * len(self.letters)

    def set_text(self, string):
        self.text = string
        self.index = 0
        self.countdown = 0.05
        self._rebuild()

    def set_color(self, color):
        self.color = color
        self._rebuild()

    def size(self):
        t = textmod.Text(self.font, self.text, fixed_width=TEXT_WIDTH, multi_line=True)
        _, w, h, _ = t.build()
        return w, h

    def step_reveal(self, dt, sounds, frame):
        n = len(self.letters)
        if self.index >= n:
            return False
        self.countdown -= dt
        if self.countdown < 0.0:
            while self.index < n:
                if self.index % 3 == 0:
                    sounds.append(frame)
                ch = self.letters[self.index][0]
                if ch in ".。":
                    delay = 0.5
                elif ch in ",、":
                    delay = 0.25
                else:
                    delay = 0.04
                self.countdown = delay + self.countdown
                self.index += 1
                if not self.countdown < 0.0:
                    break
        self.alpha = [1.0 if i < self.index else 0.0 for i in range(n)]
        return True

    def reveal_all(self):
        self.alpha = [1.0] * len(self.letters)

    def shown(self):
        return sum(1 for a in self.alpha if a >= 0.001)

    def draw(self, page):
        t = textmod.Text(self.font, self.text, fixed_width=TEXT_WIDTH, multi_line=True, color=self.color)
        tiles, _, _, _ = t.build()
        alpha_of = {tile: self.alpha[i] for i, (_, tile) in enumerate(self.letters) if tile is not None}
        for k, tile in enumerate(tiles):
            a = alpha_of.get(k, (self.color >> 24) / 255.0)
            if a < 0.001:
                continue
            color = (int(a * 255) << 24) | (self.color & 0xFFFFFF)
            w, h = tile.dst[2], tile.dst[3]
            name = fontpage.WHITE if tile.page is None else self.font.page_files[tile.page]
            page.quads.append(fontpage.Quad(name, self.x + tile.dst[0], self.y + tile.dst[1], w, h, tile.src, color))


class Holder:
    """An app.vis.Sprite picture holder: picture (None, so 0 x 0), place,
    clip rectangle, shown or not."""

    def __init__(self):
        self.image = None
        self.size = (0, 0)
        self.x, self.y = 0, IMAGE_Y
        self.clip = None
        self.visible = True

    def width(self):
        return self.size[0]

    def draw(self, page):
        """Quad.make: a holder without a picture draws nothing; the clip cuts
        the quad (whole numbers here, so the picture piece stays whole)."""
        if not self.visible or self.image is None:
            return
        px, py = self.x, self.y
        pr, pb = px + self.size[0], py + self.size[1]
        ux, uy, ur, ub = 0, 0, self.size[0], self.size[1]
        if self.clip is not None:
            cx, cy, cw, ch = self.clip
            if cx + cw <= px or pr <= cx or cy + ch <= py or pb <= cy:
                return
            if px < cx:
                ux += cx - px
                px = cx
            if cx + cw < pr:
                ur -= pr - (cx + cw)
                pr = cx + cw
            if py < cy:
                uy += cy - py
                py = cy
            if cy + ch < pb:
                ub -= pb - (cy + ch)
                pb = cy + ch
        page.quads.append(fontpage.Quad(self.image, px, py, pr - px, pb - py, (ux, uy, ur - ux, ub - uy), 0xFFFFFFFF))


class Player:
    """play.screen.Intro with hurrying allowed, inside the intro screen."""

    def __init__(self, pages, pictures, lib, strings, dt):
        self.pages, self.pictures = pages, pictures
        self.caption = Caption(lib.get("title_tall"))
        self.ui_large = lib.get("ui_large")
        self.next_text = strings["menu_next"]
        self.cur, self.nex = Holder(), Holder()
        self.index = 0
        self.state = None
        self.clock = 0.0
        self.next_visible = True
        self.timers = []                # [t, sound]
        self.sounds = []                # frames on which text-reveal plays
        self.played = []                # (frame, page sound)
        self.frame = 1
        self.done = None
        self.cut = None
        self.go("flipping", dt)

    # app.Stater.go: the old state's EXIT, the new one's ENTER, its targets.
    def go(self, name, dt):
        if self.state == "flipping":
            self.end_page()
        self.state = name
        self.clock = 0.0
        if name == "flipping":
            self.show_page(dt)
        self.next_visible = name == "idle"

    def show_page(self, dt):
        if self.index >= len(self.pages):
            return
        page = self.pages[self.index]
        if "when" in page:
            raise ValueError("pages with `when` need the story's facts (not built yet)")
        c = self.caption
        c.set_text("")
        c.set_color(int(page["color"], 0) if "color" in page else 0xFFFFFF)
        if "sound" in page:
            self.timers.append([0.0, page["sound"]])
        string = page.get("text", "")
        string = "" if string.startswith("$") else string.replace("&quote;", '"')
        c.set_text(string)
        w, h = c.size()
        c.x = int(math.floor(W * 0.5 - w * 0.5))
        c.y = int(math.floor(TEXT_CENTER_Y - h * 0.5))
        c.step_reveal(dt, self.sounds, self.frame)
        image = page.get("image")
        if image is not None and not image.startswith("$"):
            self.nex.image = "intro/" + image
            self.nex.size = self.pictures[self.nex.image].size
        self.nex.x = int(math.floor(W * 0.5 - self.nex.width() * 0.5))

    def end_page(self):
        self.cur.image, self.cur.size = self.nex.image, self.nex.size
        self.cur.x = int(math.floor(W * 0.5 - self.cur.width() * 0.5))
        self.cur.clip = None
        self.cur.visible = True
        self.nex.visible = False
        self.caption.reveal_all()

    def wipe(self):
        t = lerp_scale(self.clock, 0.0, WIPE, 0.0, 1.0)
        right = self.cur.x + self.cur.width()
        cut = math_round((self.cur.x - right) * t + right)
        self.cut = cut
        self.cur.clip = (0, 0, cut, 10000)
        self.nex.clip = (cut, 0, 10000, 10000)
        self.cur.visible = self.nex.visible = True
        if WIPE < self.clock:
            if not self.caption.step_reveal(DT, self.sounds, self.frame):
                self.go("idle", DT)

    def update(self):
        for timer in list(self.timers):    # Tween.step: done once t has reached 1
            if timer[0] >= 1.0:
                self.timers.remove(timer)
                self.played.append((self.frame, timer[1]))
            else:
                timer[0] = DT / SOUND_DELAY + timer[0]
        self.clock = DT + self.clock
        if self.state == "flipping":
            self.wipe()

    def next(self):
        assert self.next_visible, "NEXT is hidden on frame %d" % self.frame
        self.index += 1
        if self.index >= len(self.pages):
            self.done = self.frame
        else:
            self.go("flipping", DT)

    def hurry(self):
        if self.index > 0 and self.state == "flipping":
            self.go("idle", DT)

    def draw(self, lib, pictures):
        page = titlescreen.Title(lib, pictures)
        page.fill(0, 0, W, H, 0xFF000000)
        self.cur.draw(page)
        self.nex.draw(page)
        self.caption.draw(page)
        if self.next_visible:
            push_w = pictures["PushButton.png"].size[0]
            x = int(math.floor(W * 0.5 - push_w * 0.5))
            page.part("PushButton.png", x, FOOTER_Y, (0, 0, push_w, PUSH_BAND))
            page.button_text(self.ui_large, self.next_text, x, FOOTER_Y, push_w, PUSH_BAND, GREEN)
        return page.quads


def intro_pages(assets):
    root = ET.parse(os.path.join(assets, "data", "Intro.xml")).getroot()
    return [dict(p.attrib) for p in root.iter("page")]


def run(assets, lib, pictures, strings):
    """Plays the fixed run. Returns the timeline and the snapshot frames."""
    p = Player(intro_pages(assets), pictures, lib, strings, DT)
    frames, snaps, events = [], {}, {}
    entered = {0: 1}                    # page -> frame its flipping began
    idle_at = {}

    def plan(frame):
        """What the run does on this frame, decided from what happened so
        far (so the Rust test can follow the same rules)."""
        page = p.index
        if page in idle_at:
            if frame == idle_at[page] + 20:
                return "next"
        if page == 2 and frame == entered[2] + 10:
            return "hurry"
        if page == 3 and frame == entered[3] + 70:
            return "hurry"
        return None

    frame = 1
    while p.done is None and frame < 3000:
        p.frame = frame
        p.update()
        what = plan(frame)
        if what == "next":
            events[frame] = "next"
            p.next()
            if p.done is None:
                entered[p.index] = frame
        elif what == "hurry":
            events[frame] = "hurry"
            p.hurry()
        if p.state == "idle" and p.index not in idle_at and p.done is None:
            idle_at[p.index] = frame
        frames.append({
            "frame": frame, "page": p.index, "state": p.state, "cut": p.cut,
            "shown": p.caption.shown(), "next": p.next_visible,
        })
        p.cut = None
        # Snapshots, drawn at the end of the frame.
        name = None
        if p.index == 0 and idle_at.get(0) == frame - 5:
            name = "page1_rest"
        elif p.index == 1 and frame == entered[1] + 30:
            name = "page2_wipe"
        elif p.index == 1 and p.state == "flipping" and p.caption.shown() == 20 \
                and all(n != "page2_typing" for n, _ in snaps.values()):
            name = "page2_typing"
        elif p.index == 1 and idle_at.get(1) == frame - 5:
            name = "page2_rest"
        elif p.index == 2 and frame == entered[2] + 11:
            name = "page3_hurried"
        elif p.index == 3 and idle_at.get(3) == frame - 5:
            name = "page4_rest"
        elif p.index == 4 and idle_at.get(4) == frame - 5:
            name = "page5_rest"
        if name:
            snaps[frame] = (name, p.draw(lib, pictures))
        frame += 1
    timeline = {
        "frames": frames,
        "events": [{"frame": f, "what": w} for f, w in sorted(events.items())],
        "text_reveal": p.sounds,
        "page_sounds": p.played,
        "entered": entered,
        "idle": idle_at,
        "done": p.done,
        "snapshots": {name: f for f, (name, _) in snaps.items()},
    }
    return timeline, {name: quads for f, (name, quads) in snaps.items()}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    assets, out = argv[1], argv[2]
    lib = fonts.FontLib(assets)
    pictures = {f: Image.open(os.path.join(assets, "fonts", f)) for f in fontpage.sheet_files(lib)}
    pictures["PushButton.png"] = Image.open(os.path.join(assets, "PushButton.png"))
    for page in intro_pages(assets):
        name = "intro/" + page["image"]
        pictures[name] = Image.open(os.path.join(assets, name))
    strings = titlescreen.text_items(assets)
    timeline, snaps = run(assets, lib, pictures, strings)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump(timeline, f, indent=1)
    for name in SNAPSHOTS:
        if name not in snaps:
            raise SystemExit("snapshot %s was not taken" % name)
        data = fontpage.draw(snaps[name], pictures)
        with open(os.path.join(out, name + ".rgba"), "wb") as f:
            f.write(data)
        im = Image.frombytes("RGBA", (W, H), data).convert("RGB")
        im.save(os.path.join(out, name + ".png"))
        im.resize((W * 3, H * 3), Image.NEAREST).save(os.path.join(out, name + "_x3.png"))
        print("%s: frame %d, %d quads" % (name, timeline["snapshots"][name], len(snaps[name])))
    print("%d frames; the pages end on frame %d; text-reveal on %d frames -> %s"
          % (len(timeline["frames"]), timeline["done"], len(timeline["text_reveal"]), out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
