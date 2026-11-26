"""The day screen at the start of day 1, milestones 4a, 4b and 4c (docs/milestone-4.md):
the booth as its constructor builds it on desktop, the day's opening card
typing the date and falling away, and the border scene's background and
booth button, frame by frame at 1/60 s a frame. Written from the code
(docs/booth-screen.md, read for this step) before the Rust, and drawn with
the same quad rules as fontpage.py.

    python -I scripts/reference/boothscreen.py <assets dir> <out dir>

for example `extracted/art/assets` and `extracted/previews/m4c` (gitignored).
It plays the first FRAMES frames and writes:

- timeline.json: for every frame, the booth's and the border's states, the
  opening card's y and whether it is shown, how many letters of the date
  are shown, the booth button's look, the shutter's state and openT, the
  switch's look, whether the game is paused, the game clock, the
  rulebook's place, placement, state, drag and shadow, the cursor the
  parts chose; the frames on which each sound starts; the frame of
  `start-intro`; the input, frame by frame (`input`: the mouse's x and y,
  its button, Escape), which the Rust test plays as real presses;
- <name>.rgba for the frames in SNAPSHOTS (570 x 320 x 4 bytes, alpha 255),
  each also as a PNG and, enlarged 3 times, as _x3.png to look at.

port/core/tests/day.rs runs the port's game through the same frames and
compares both, byte for byte and frame for frame.

Since milestone 4b the run has input (SCRIPT): after the intro has begun,
the shutter switch is clicked (the shutter opens), Escape pauses the game
in the middle of the opening, Escape again presses RESUME, and later the
switch closes the shutter. Since milestone 4c the mouse also moves
(RULEBOOK_SCRIPT): the rulebook is hovered, pressed and dragged closed
over the counter and let go (home again), dragged onto the desk and let go,
hovered over a button, thrown, dragged back over the counter (home again),
and clicked at its dock (rulebook.py).

What is left out on purpose (docs/milestone-4.md, "4a"): the border
scene's figures (milestone 6; only the walk-in figure's distance is kept,
for the moment it starts the booth's intro), the day's other papers (the
bulletin and the transcript, 4e), the booth's engine, every click but the
switch's and the rulebook's.

The rules, as read (docs/booth-screen.md):

- Frames. The screen is built on frame 1 by an instant screen change and
  updated in the same frame (docs/milestone-3.md, 3b). The tree updates
  the booth (Booth.update, then its children), then the border.
- Clocks (app.Clock.update): a clock's first update gives dt 0, every
  later one the time since the one before, at most 0.1 s (maxDeltaTime):
  the frame's time, or after the pause the paused frames' time too. The booth and the border have their own
  clocks, made with the screen; the typing (stepReveal) and the booth
  button's blink use the game's clock, which here starts with the run
  (time = frames x 1/60, added up).
- app.Stater / app.State: as read in full for this step (see Stater
  below).
- The opening card: a black fill 570 x 217 and the date typed in
  title_tall, colour 0x00FFFFFF, several lines; the text is the long date
  and a line break (a story day's title is the empty text, not missing);
  x = floor(285 - w / 2), y = floor(108.5 - h / 2 - 20). One stepReveal
  when it is made, then one every frame in `off`.
- The shutter (Shutter, docs/booth-screen.md): `closed` (0.35 s to openT 0
  along BOUNCEBACK(0.1, 1), `shutter-drop`, the switch `down`) and `open`
  (1.0 s to openT 1 along SMOOTHERSTEP(0, 1), `shutter-rise`, the switch
  `up`); it steps with the game's clock, after Booth.update. A click on
  the switch (button-down on the press, button-up on the release) toggles
  it once the booth's parts take input (from the intro on).
- The pause (Game.update, the `paused` state, docs/milestone-4.md 4b):
  Escape pauses (`button-drop`); while paused the screen is not updated
  and no game time passes; Escape pressed and let go presses RESUME
  (button-down, then button-up and `hover-up`).
- The walk-in: the free leaving figure follows `enter-right` (60 units,
  speed 10) from its start; each border frame adds dt x 10 (dt from the
  border's clock); when the distance reaches 60, `start-intro`: the
  booth goes to `intro`, the border to `ready-to-call`.
"""

import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import faces  # noqa: E402
import fontpage  # noqa: E402
import fonts  # noqa: E402
import gdate  # noqa: E402
import inputs  # noqa: E402
import rulebook as rulebookmod  # noqa: E402
import text as textmod  # noqa: E402
import titlescreen  # noqa: E402
from introscreen import built_letters, lerp_scale  # noqa: E402
from PIL import Image  # noqa: E402

W, H = fontpage.W, fontpage.H
DT = 1.0 / 60.0
FRAMES = 1250

# Desktop layout values (booth-layout.md, scripts/reference/layout.py).
BOOTH_Y = 103
BOOTH_W, BOOTH_H = 570, 217
WALL_W, WALL_H = 178, 107
COUNTER_Y = 105
CONSOLE_Y = 166
DESK_X, DESK_W, DESK_H = 178, 392, 217
SHUTTER_SWITCH = (150, 4)
STAMP_BAR = (570, 24)
CONSOLE_CLOCK = (9, 21)
CONSOLE_DATE = (4, 48)
CONSOLE_COUNT = (86, 42)
CONSOLE_WEIGHT = (164, 34)
OUTER_BOOTH_BUTTON = (146, 65)
BORDER_H = 103

DATE_COLOR = 0xFF422A1C          # ConsoleEnt's static colours
COUNT_COLOR = 0xFF6A522F
HINT_COLOR, HINT_BACK = 0xFF322525, 0xFF191212
SHADOW_COLOR = 0xFF191212        # the shutter's shadow, 25/255, 18/255, 18/255
DAY1 = 2445296.5                 # 23 November 1982 (value-helpers.md)

WALK_LENGTH, WALK_SPEED = 60.0, 10.0   # Paths.xml `enter-right`, default speed

SNAPSHOTS = ["card_typing", "card_full", "card_falling", "card_bounce", "booth_highlight", "booth_normal",
             "shutter_opening", "shutter_open", "shutter_closing",
             "rulebook_lifted", "rulebook_closed_drag", "rulebook_returning", "rulebook_opening", "rulebook_open",
             "rulebook_thrown", "rulebook_closing", "rulebook_home"]
MAX_DT = 0.1                     # app.Clock.maxDeltaTime

# The input (milestone 4b), in frames after start-intro: what is pressed on
# which frame and let go 3 frames later.
SCRIPT = [(150, "switch"), (170, "escape"), (230, "escape"), (310, "switch")]
HOLD = 3
SWITCH_AT = (164, 118)            # the middle of the shutter switch (28 x 23 at 150, 107)
SWITCH_RECT = (150, 107, 28, 23)

# The rulebook's script (milestone 4c), in frames after start-intro: the
# mouse's place and whether its button is held, frame by frame. Before it
# the mouse rests on the shutter switch (where 4b's clicks are).
DOCK_AT = (126, 294)              # the middle of the rulebook at its dock (113, 174 + 103)
DAY1_RULES = "RuleNeedPassport;RuleArstotzkaOnly;"


def rulebook_script():
    out = {}

    def hold(a, b, at, down):
        for o in range(a, b):
            out[o] = (at[0], at[1], down)

    def move(a, b, p, q, down):
        for o in range(a, b):
            t = (o - a + 1) / float(b - a)
            out[o] = (int(math.floor(p[0] + (q[0] - p[0]) * t)), int(math.floor(p[1] + (q[1] - p[1]) * t)), down)
    hold(360, 370, DOCK_AT, False)                    # over the closed rulebook: the hand
    hold(370, 375, DOCK_AT, True)                     # pressed: lifted 6 pixels, paper-totop
    move(375, 390, DOCK_AT, (60, 200), True)          # dragged closed over the counter
    hold(390, 400, (60, 200), True)
    hold(400, 460, (60, 200), False)                  # let go: back to the dock
    hold(460, 462, DOCK_AT, False)
    hold(462, 466, DOCK_AT, True)                     # pressed again
    move(466, 496, DOCK_AT, (400, 200), True)         # onto the desk: open, with the shadow
    hold(496, 530, (400, 200), True)                  # held still: the speed dies away
    hold(530, 570, (400, 200), False)                 # let go: it stays
    hold(570, 590, (440, 166), False)                 # over "Basic Rules": the hand
    hold(590, 592, (337, 240), False)
    hold(592, 594, (337, 240), True)                  # pressed on the page
    move(594, 600, (337, 240), (217, 240), True)      # thrown to the left, fast
    hold(600, 640, (217, 240), False)                 # it slides on and stops
    hold(640, 642, (300, 240), False)
    hold(642, 644, (300, 240), True)                  # pressed on the page
    move(644, 664, (300, 240), (90, 200), True)       # back over the counter: closed
    hold(664, 670, (90, 200), True)
    hold(670, 760, (90, 200), False)                  # let go: back to the dock
    hold(760, 762, DOCK_AT, False)
    hold(762, 764, DOCK_AT, True)                     # a click on it at its dock
    hold(764, 820, DOCK_AT, False)
    return out


RULEBOOK_SCRIPT = rulebook_script()
RULEBOOK_SNAPS = {372: "rulebook_lifted", 395: "rulebook_closed_drag", 405: "rulebook_returning",
                  500: "rulebook_opening", 565: "rulebook_open", 603: "rulebook_thrown", 667: "rulebook_closing",
                  815: "rulebook_home"}


# --- app.Interp ---------------------------------------------------------

class Interp:
    """app.Interp: a target value b reached along a curve."""

    def __init__(self, kind, b, *params):
        self.kind, self.b, self.params = kind, b, params

    def get(self, a, interp):
        t = lerp_scale(interp, 0.0, 1.0, 0.0, 1.0)
        if self.kind == "STEP":
            return a if t < self.params[0] else self.b
        if self.kind == "LINEAR":
            return lerp(a, self.b, t)
        if self.kind == "SMOOTHERSTEP":
            e0, e1 = self.params
            d = max(0.0, min(1.0, (t - e0) / (e1 - e0)))
            return lerp(a, self.b, ((d * 6.0 - 15.0) * d + 10.0) * d * d * d)
        if self.kind == "BOUNCEBACK":
            perc, count = self.params
            n1 = float(count + 1)
            half = float(count) + 0.5
            k = math.floor(half * t + 0.5)
            first = 1.0 / n1
            kk = float(int(k)) / n1
            amp = 1.0
            if first <= kk:
                amp = (kk - first) * (0.0 - perc) + perc
            c = math.cos(half * math.pi * t)
            return lerp(a, self.b, 1.0 - abs(c) * amp)
        raise ValueError(self.kind)


def lerp(a, b, t):
    """app.Interp.lerp for numbers, else a below t 0.5 and b from it."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a if t < 0.5 else b
    return (b - a) * t + a


# --- app.Stater ---------------------------------------------------------

class State:
    def __init__(self, name):
        self.name = name
        self.interp_duration = 0.0
        self.duration = -1.0
        self.after = None
        self.step_time = 0.0
        self.funcs = []                # [when, func, done]; when: ENTER, STEP, EXIT or ("AT", t)
        self.targets = []              # (object, {prop: value or Interp})

    def enter(self, snapshot):
        for f in self.funcs:
            if f[0] == "ENTER":
                f[1]()
            f[2] = False
        self.step_time = 0.0
        self.apply(snapshot, 0.0 if snapshot is not None else 1.0)

    def exit(self):
        for f in self.funcs:
            if f[0] == "EXIT":
                f[1]()

    def step(self, dt):
        self.step_time = dt + self.step_time
        for f in self.funcs:
            if f[0] == "STEP":
                f[1]()
            elif isinstance(f[0], tuple) and not f[2] and f[0][1] <= self.step_time:
                f[2] = True
                f[1]()

    def snapshot(self):
        return [(obj, {p: getattr(obj, p) for p in props}) for obj, props in self.targets]

    def apply(self, snapshot, interp):
        t = 1.0 if interp is None else interp
        for obj, props in self.targets:
            for prop, default in props.items():
                value = default
                if snapshot is not None:
                    for sobj, sprops in snapshot:
                        if sobj is obj and prop in sprops:
                            value = sprops[prop]
                            break
                if isinstance(value, Interp):
                    value = value.b
                if isinstance(default, Interp):
                    value = default.get(value, t)
                else:
                    value = lerp(value, default, t)
                setattr(obj, prop, value)


class Stater:
    def __init__(self):
        self.states = {}
        self.cur = None
        self.snapshot = None
        self.countdown = 0.0

    def add(self, name):
        s = State(name)
        self.states[name] = s
        return s

    def go(self, name, instant=False):
        new = self.states[name]
        self.countdown = 0.0
        if self.cur is not None:
            self.cur.exit()
        else:
            instant = True
        if not instant:
            self.snapshot = new.snapshot()
            self.cur = new
            new.enter(self.snapshot)
            self.countdown = new.interp_duration
            if self.countdown == 0.0:
                new.apply(None, None)
        else:
            self.cur = new
            new.enter(None)
            new.apply(None, None)
        # needsStep is not modelled: every state here either blends or has
        # targets that are already in place.
        if self.countdown == 0.0:
            new.apply(self.snapshot, 1.0)

    def step(self, dt):
        s = self.cur
        if self.countdown == 0.0:
            if s.duration < 0.0 or s.after is None or s.step_time < s.duration:
                s.step(dt)
            else:
                self.go(s.after)
        else:
            t = 1.0 - self.countdown / s.interp_duration
            s.apply(self.snapshot, min(1.0, t))
            if 1.0 <= t:
                self.countdown = 0.0
                if s.duration == 0.0 and s.after is not None:
                    self.go(s.after)
            else:
                self.countdown = self.countdown - dt
                if self.countdown == 0.0:
                    self.countdown = -1.0


class Clock:
    """app.Clock with a fixed frame: dt 0 on the first update, then the time
    since the last update (the frame, and any frames it missed), capped."""

    def __init__(self):
        self.started = False
        self.dt = 0.0
        self.missed = 0.0

    def update(self):
        since = self.missed + DT
        self.dt = 0.0 if not self.started else (MAX_DT if MAX_DT < since else since)
        self.missed = 0.0
        self.started = True

    def skip(self):
        self.missed = self.missed + DT


# --- the parts ----------------------------------------------------------

class RevealText:
    """play.ui.RevealTextEnt (as introscreen.Caption, with no fixed width)."""

    def __init__(self, font):
        self.font = font
        self.text, self.color, self.multi_line = "", 0, False
        self.x = self.y = 0
        self.index, self.countdown = 0, 0.0
        self.alpha, self.letters = [], []
        self.visible = True

    def _rebuild(self):
        self.letters = built_letters(self.font, self.text, 0, self.multi_line)
        self.alpha = [(self.color >> 24) / 255.0] * len(self.letters)

    def set_color(self, color):
        self.color = color
        self._rebuild()

    def set_text(self, string):
        self.text, self.index, self.countdown = string, 0, 0.05
        self._rebuild()

    def set_multi_line(self, on):
        self.multi_line = on
        self._rebuild()

    def size(self):
        _, w, h, _ = textmod.Text(self.font, self.text, multi_line=self.multi_line).build()
        return w, h

    def step_reveal(self, sounds, frame):
        n = len(self.letters)
        if self.index >= n:
            return False
        self.countdown -= DT
        if self.countdown < 0.0:
            while self.index < n:
                if self.index % 3 == 0:
                    sounds.append((frame, "text-reveal"))
                ch = self.letters[self.index][0]
                delay = 0.5 if ch in ".。" else 0.25 if ch in ",、" else 0.04
                self.countdown = delay + self.countdown
                self.index += 1
                if not self.countdown < 0.0:
                    break
        self.alpha = [1.0 if i < self.index else 0.0 for i in range(n)]
        return True

    def shown(self):
        return sum(1 for a in self.alpha if a >= 0.001)

    def draw(self, page, ox, oy):
        if not self.visible:
            return
        t = textmod.Text(self.font, self.text, multi_line=self.multi_line, color=self.color)
        tiles, _, _, _ = t.build()
        alpha_of = {tile: self.alpha[i] for i, (_, tile) in enumerate(self.letters) if tile is not None}
        for k, tile in enumerate(tiles):
            a = alpha_of.get(k, (self.color >> 24) / 255.0)
            color = (int(a * 255) << 24) | (self.color & 0xFFFFFF)
            name = fontpage.WHITE if tile.page is None else self.font.page_files[tile.page]
            page.quads.append(fontpage.Quad(name, ox + self.x + tile.dst[0], oy + self.y + tile.dst[1],
                                            tile.dst[2], tile.dst[3], tile.src, color))


class Group:
    """The opening card's group entity: `active` and `y` are what its
    states move."""

    def __init__(self):
        self.active = True
        self.y = 0.0


class Shutter:
    """What the shutter's states move."""

    def __init__(self):
        self.open_t = 0.0


class Flags:
    """An entity's switch 8 or 4, as the states set them (not drawn)."""

    def __init__(self):
        self.input = True


def clock_picture(assets, hour):
    """ConsoleClock.set_hour: a 16 x 16 picture."""
    size = 16.0
    pic = faces.Image(16, 16)
    hand = faces.Image(32, 16, DATE_COLOR)
    pin = faces.Image.load(os.path.join(assets, "ClockPin.png"))
    minute = math.fmod(hour, 1.0)
    a_min = math.pi * 0.5 - (math.pi + math.pi) * minute
    a_hour = math.pi * 0.5 - (math.pi + math.pi) * (hour / 12.0)
    dark = hour >= 18.0 or (hour > 16.0 and math.fmod(hour * 20.0, 1.0) > 0.75)
    pic.px = [DATE_COLOR if dark else 0] * (16 * 16)
    for length, thick, angle in ((size * 0.5 / hand.width, 1.0 / hand.height, a_min),
                                 (size * 0.5 * 0.75 / hand.width, 2.0 / hand.height, a_hour)):
        m = faces.Affine()
        m.translate(0.0, -hand.height * 0.5)
        m.scale(length, thick)
        c, s = math.cos(-angle), math.sin(-angle)
        m._then(c, -s, 0.0, s, c, 0.0)
        m.translate(size * 0.5, size * 0.5)
        pic.draw(hand, m)
    for y in range(pin.height):                 # paste, REPLACE
        for x in range(pin.width):
            pic.px[(7 + y) * 16 + 7 + x] = pin.px[y * pin.width + x]
    out = Image.new("RGBA", (16, 16))
    out.putdata([((p >> 16) & 255, (p >> 8) & 255, p & 255, p >> 24) for p in pic.px])
    return out


class Day:
    def __init__(self, assets, lib, pictures, strings):
        self.assets, self.lib, self.pictures, self.strings = assets, lib, pictures, strings
        self.frame = 1
        self.time = 0.0
        self.sounds = []
        self.events = {}
        self.booth_clock, self.border_clock = Clock(), Clock()
        self.booth_time = 0.0

        # The booth (constructor order; docs/booth-screen.md).
        self.card = Group()
        self.reveal = RevealText(lib.get("title_tall"))
        self.reveal.set_color(0xFFFFFF)
        y, m0, d = gdate.split(DAY1)
        long_date = strings["date_verbose"].replace("$month", strings["month_%d" % (m0 + 1)]) \
            .replace("$day", strings["day_%d" % d]).replace("$year", str(y))
        self.reveal.set_text(long_date + "\n" + "")
        self.reveal.set_multi_line(True)
        w, h = self.reveal.size()
        self.reveal.x = int(math.floor(BOOTH_W * 0.5 - w * 0.5))
        self.reveal.y = int(math.floor(BOOTH_H * 0.5 - h * 0.5 - 20.0))
        self.reveal.step_reveal(self.sounds, self.frame)
        self.date_text = gdate.format_date(DAY1, "%y.%m.%d")
        self.sounds.append((1, "border-ambient"))
        self.sounds.append((1, "booth-ambient"))
        self.booth_flags = Flags()
        self.booth = Stater()
        off = self.booth.add("off")
        off.funcs = [["ENTER", lambda: setattr(self.booth_flags, "input", False), False],
                     ["STEP", lambda: self.reveal.step_reveal(self.sounds, self.frame), False],
                     ["EXIT", lambda: setattr(self.booth_flags, "input", True), False]]
        off.targets = [(self.card, {"active": True, "y": 0.0})]
        intro = self.booth.add("intro")
        intro.interp_duration, intro.duration, intro.after = 1.0, 0.0, "empty"
        intro.funcs = [["ENTER", lambda: self.sounds.append((self.frame, "booth-intro")), False],
                       ["EXIT", lambda: setattr(self.reveal, "visible", False), False]]
        intro.targets = [(self.card, {"active": Interp("STEP", False, 1.0),
                                      "y": Interp("BOUNCEBACK", float(BOOTH_H), 0.2, 1)})]
        empty = self.booth.add("empty")
        empty.targets = [(self.card, {"active": False})]
        self.booth.go("off", True)
        # BoothEngine.start: the day's papers (here only the rulebook; 4e
        # adds the bulletin and the transcript).
        self.rulebook = rulebookmod.Rulebook(assets, lib, pictures, DAY1_RULES, DT, self.sounds)
        self.weight_text = "---"
        self.weight = None
        self.clock = clock_picture(assets, 6.0)
        pictures["made/clock"] = self.clock

        # The shutter: closed at once; its `shutter-drop` falls in the
        # screen change's frame, which drops one-shot sounds, and its switch
        # is not given to it yet.
        self.shutter_obj = Shutter()
        self.switch_look = "down"
        self.switch_given = False
        self.shutter = Stater()
        closed = self.shutter.add("closed")
        closed.interp_duration = 0.35
        closed.funcs = [["ENTER", lambda: self.shutter_sound("shutter-drop", "down"), False]]
        closed.targets = [(self.shutter_obj, {"open_t": Interp("BOUNCEBACK", 0.0, 0.1, 1)})]
        opened = self.shutter.add("open")
        opened.interp_duration = 1.0
        opened.funcs = [["ENTER", lambda: self.shutter_sound("shutter-rise", "up"), False]]
        opened.targets = [(self.shutter_obj, {"open_t": Interp("SMOOTHERSTEP", 1.0, 0.0, 1.0)})]
        self.shutter.go("closed", True)
        self.switch_given = True

        # The border scene.
        self.walk = 0.0
        self.walk_done = False
        self.button_look = "normal"
        self.border = Stater()
        self.border.add("off")
        ready = self.border.add("ready-to-call")
        ready.funcs = [["STEP", self.blink, False]]
        self.border.go("off", True)

    def shutter_sound(self, sound, look):
        if self.switch_given:
            self.sounds.append((self.frame, sound))
            self.switch_look = look

    def switch_click(self):
        """Booth.shutterSwitch_onClick (the booth is never busy-with-border
        here, and closeShutter does nothing without a traveler)."""
        self.shutter.go("closed" if self.shutter.cur.name == "open" else "open")

    def skip(self):
        """A frame the screen is hidden under the pause."""
        self.booth_clock.skip()
        self.border_clock.skip()

    def blink(self):
        self.button_look = "normal" if 0.375 < math.fmod(self.time, 0.75) else "highlight"

    def update(self):
        self.time = DT + self.time
        # Booth.update, then its children (nothing in them moves yet).
        self.booth_clock.update()
        self.booth_time = self.booth_clock.dt + self.booth_time
        self.booth.step(self.booth_clock.dt)
        weight = ""                              # no traveler at his place
        if weight != self.weight:
            self.weight = weight
            self.weight_text = weight.replace("kg", "")
        # The booth's children: the shutter, with the game's clock; then
        # the papers.
        self.shutter.step(DT)
        self.rulebook.frame = self.frame
        self.rulebook.update(DT, self.frame)
        # Border.update: its clock, its states, then the figures.
        self.border_clock.update()
        self.border.step(self.border_clock.dt)
        if not self.walk_done:
            self.walk = self.border_clock.dt * WALK_SPEED + self.walk
            if self.walk >= WALK_LENGTH:
                self.walk_done = True
                self.events["start-intro"] = self.frame
                self.booth.go("intro")
                self.border.go("ready-to-call")

    def draw(self):
        lib, pictures = self.lib, self.pictures
        page = titlescreen.Title(lib, pictures)
        by = BOOTH_Y
        # Layer -1: the shutter's shadow (the shutter at x -1).
        strip_h = 20
        top = (-40.0 - WALL_H) * self.shutter_obj.open_t + WALL_H
        page.fill(-1, by + int(math.floor(min(0.0, top - WALL_H + 40.0))), 180, WALL_H, SHADOW_COLOR)
        # Layer 0, the booth's children in order.
        for i in range(6):
            y = int(math.floor(min(i * (WALL_H / 6.0), top - (6 - i) * strip_h * 0.5 - strip_h * 0.5)))
            page.part("Shutter.png", -1, by + y, (0, 20 * i, 180, 20))
        page.picture("Counter.png", 0, by + COUNTER_Y)
        page.picture("ConsoleUnder.png", 0, by + CONSOLE_Y)
        switch = "ShutterSwitchDown.png" if self.switch_look == "down" else "ShutterSwitchUp.png"
        page.picture(switch, SHUTTER_SWITCH[0], by + SHUTTER_SWITCH[1])
        page.picture("Desk.png", DESK_X, by + 0)
        ui = lib.get("ui_regular")
        hint = self.strings["booth_dragdocs"]
        _, hw, hh, _ = textmod.Text(ui, hint).build()
        hx = int(math.floor(math.floor(DESK_W * 0.5 + DESK_X) - hw * 0.5))
        hy = (DESK_H + 0.0 - 5.0) - hh
        page.text(ui, hint, hx, by + hy, color=HINT_COLOR, background=HINT_BACK, padding_x=6, padding_y=2)
        # The papers.
        self.rulebook.draw(page)
        # The console, moved to the end of the booth's children then.
        cy = by + CONSOLE_Y
        page.picture("Console.png", 0, cy)
        page.picture("made/clock", CONSOLE_CLOCK[0], cy + CONSOLE_CLOCK[1])
        digits = lib.get("digits")
        page.text(digits, self.date_text, CONSOLE_DATE[0], cy + CONSOLE_DATE[1] - digits.ascent, color=DATE_COLOR)
        page.text(digits, "00", CONSOLE_COUNT[0], cy + CONSOLE_COUNT[1] - digits.ascent + digits.cap_height,
                  color=COUNT_COLOR)
        if self.weight_text:
            raise ValueError("a weight is not drawn in 4a")
        # The stamp bar, closed: 10 pixels show at the desk's right edge.
        bx, sy = STAMP_BAR[0] - 10, by + STAMP_BAR[1]
        top_h = pictures["StampBarTop.png"].size[1]
        mid_h = pictures["StampBarMid.png"].size[1]
        page.picture("StampBarTop.png", bx, sy)
        page.picture("StampBarBot.png", bx, sy + top_h + mid_h)
        page.picture("StampBarMid.png", bx, sy + top_h)
        # The opening card.
        if self.card.active:
            gy = by + self.card.y
            page.fill(0, gy, BOOTH_W, BOOTH_H, 0xFF000000)
            self.reveal.draw(page, 0, gy)
        # The border scene: its background, then the booth button.
        page.picture("CheckpointBack.png", 0, 0)
        band = 0 if self.button_look == "normal" else BORDER_H - OUTER_BOOTH_BUTTON[1]
        page.part("OuterBooth.png", OUTER_BOOTH_BUTTON[0], OUTER_BOOTH_BUTTON[1],
                  (0, band, 56, BORDER_H - OUTER_BOOTH_BUTTON[1]))
        return page.quads


PICTURES = ["Shutter.png", "Counter.png", "ConsoleUnder.png", "Console.png", "ShutterSwitchDown.png",
            "ShutterSwitchUp.png", "Desk.png",
            "StampBarTop.png", "StampBarMid.png", "StampBarBot.png", "CheckpointBack.png", "OuterBooth.png"]


def run(assets, lib, pictures, strings):
    day = Day(assets, lib, pictures, strings)
    frames, snaps, host_input = [], {}, []
    start = None
    paused = False
    script = []                      # (frame pressed, what), set once start-intro is known
    switch_pressing = False
    resume_pressing = False
    opened_at = closed_at = None
    inp = inputs.Input()
    rulebook_ent = object()          # the rulebook's input identity
    for frame in range(1, FRAMES + 1):
        day.frame = frame
        held = {what for at, what in script if at <= frame < at + HOLD}
        released = {what for at, what in script if frame == at + HOLD}
        # The host's input this frame: the mouse rests on the shutter switch
        # (pressed for its clicks), then follows the rulebook's script.
        mx, my, down = SWITCH_AT[0], SWITCH_AT[1], "switch" in held
        if start is not None and (frame - start) in RULEBOOK_SCRIPT:
            mx, my, down = RULEBOOK_SCRIPT[frame - start]
        elif start is not None and frame - start > max(RULEBOOK_SCRIPT):
            mx, my, down = RULEBOOK_SCRIPT[max(RULEBOOK_SCRIPT)]
        escape = "escape" in held
        host_input.append([mx, my, down, escape])
        inp.update([False] * 11, [(down, (float(mx), float(my)), False), (False, (0.0, 0.0), True),
                                  (False, (0.0, 0.0), True)], frame * DT)
        # Game.update: the pause key first (Escape just down, the game on,
        # the day screen can pause); Escape is then masked until let go.
        escape_masked = getattr(day, "escape_masked", False)
        if "escape" in released:
            day.escape_masked = False
        just_down = {what for at, what in script if frame == at}
        if "escape" in just_down and not paused:
            paused = True
            day.escape_masked = True
            escape_masked = True
            day.sounds.append((frame, "button-drop"))
        # The tree's update: the day, unless hidden under the pause.
        if paused:
            day.skip()
        else:
            day.update()
        if start is None and "start-intro" in day.events:
            start = day.events["start-intro"]
            script = [(start + after, what) for after, what in SCRIPT]
        # The input: the pause screen's RESUME (Escape, the back button),
        # then the day's parts when not paused: the rulebook (a later child
        # of the booth, so first), then the shutter switch.
        if paused and not escape_masked:
            if "escape" in held and not resume_pressing:
                resume_pressing = True
                day.sounds.append((frame, "button-down"))
            elif "escape" in released and resume_pressing:
                resume_pressing = False
                day.sounds.append((frame, "button-up"))
                paused = False
                day.sounds.append((frame, "hover-up"))
        if not paused and day.booth_flags.input:
            day.rulebook.frame = frame
            day.rulebook.react(inp, rulebook_ent)
            p = inp.pointers[0]
            if p.capturing is None and inputs.inside(SWITCH_RECT, p.world[0], p.world[1]):
                p.set_cursor("HAND")
            if "switch" in held and not switch_pressing:
                switch_pressing = True
                day.sounds.append((frame, "button-down"))
            elif "switch" in released and switch_pressing:
                switch_pressing = False
                day.sounds.append((frame, "button-up"))
                day.switch_click()
                if day.shutter.cur.name == "open":
                    opened_at = frame
                else:
                    closed_at = frame
        rb = day.rulebook.state()
        frames.append({
            "frame": frame, "booth": day.booth.cur.name, "border": day.border.cur.name,
            "card": day.card.active, "card_y": day.card.y, "shown": day.reveal.shown(),
            "button": day.button_look, "shutter": day.shutter.cur.name, "open_t": day.shutter_obj.open_t,
            "switch": day.switch_look, "paused": paused, "time": day.time,
            "booth_time": day.booth_time,
            "rb_x": rb["x"], "rb_y": rb["y"], "rb_placement": rb["placement"], "rb_state": rb["state"],
            "rb_dragging": rb["dragging"], "rb_shadow": rb["shadow"],
            "cursor": None if paused else inp.pointers[0].cursor,
        })
        name = None
        if frame == 40:
            name = "card_typing"
        elif start is not None and frame == start:
            name = "card_full"
        elif start is not None and frame == start + 20:
            name = "card_falling"
        elif start is not None and frame == start + 48:
            name = "card_bounce"
        elif start is not None and frame > start + 70 and day.button_look == "highlight" \
                and all(n != "booth_highlight" for n, _ in snaps.values()):
            name = "booth_highlight"
        elif start is not None and frame > start + 70 and day.button_look == "normal" \
                and all(n != "booth_normal" for n, _ in snaps.values()):
            name = "booth_normal"
        elif opened_at is not None and frame == opened_at + 12:
            name = "shutter_opening"
        elif opened_at is not None and closed_at is None and not paused and day.shutter_obj.open_t == 1.0 \
                and all(n != "shutter_open" for n, _ in snaps.values()):
            name = "shutter_open"
        elif closed_at is not None and frame == closed_at + 9:
            name = "shutter_closing"
        elif start is not None and (frame - start) in RULEBOOK_SNAPS:
            name = RULEBOOK_SNAPS[frame - start]
        if name:
            snaps[frame] = (name, day.draw())
    timeline = {
        "frames": frames,
        "sounds": [{"frame": f, "id": s} for f, s in day.sounds],
        "start_intro": start,
        "script": [{"frame": at, "what": what, "hold": HOLD} for at, what in script],
        "input": host_input,
        "snapshots": {name: f for f, (name, _) in snaps.items()},
        "date": day.date_text,
        "card_text": day.reveal.text,
        "card_xy": [day.reveal.x, day.reveal.y],
        "rulebook_mask": day.rulebook.mask,
        "rulebook_marks": [[v.name, v.kind, v.x, v.y, v.size[0], v.size[1]] for v in day.rulebook.placed],
    }
    return timeline, {name: quads for f, (name, quads) in snaps.items()}


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 1
    assets, out = argv[1], argv[2]
    lib = fonts.FontLib(assets)
    pictures = {f: Image.open(os.path.join(assets, "fonts", f)) for f in fontpage.sheet_files(lib)}
    for name in PICTURES:
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
    print("%d frames; start-intro on frame %s; date %r; card text %r at %s -> %s"
          % (len(timeline["frames"]), timeline["start_intro"], timeline["date"], timeline["card_text"],
             timeline["card_xy"], out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
