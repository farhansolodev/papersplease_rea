"""The rulebook on the desk at the start of a day, milestone 4c
(docs/milestone-4.md, "4c"): a play.day.booth.Paper and its DeskItem, as
the booth makes it (Booth.engine_onPapersAdded, the Paper constructor) and
as it reacts and moves each frame (DeskItem.react and update). Built on
deskmove.py (the movement, docs/desk-movement.md), pages.py (the page
layout, docs/page-layout.md) and deskpics.py (clipping and picking a mark,
docs/desk-pictures.md). Used by boothscreen.py.

What is added here to those three:

- the page mask from Facts.xml's <rulebook> and the day's rules;
- TouchDrag with its own app.Clock (a clock started at the press gives dt 0
  on its first update; later the time since its last update, at most 0.1 s);
- DeskItem.react: getPointerOver on the item's rectangle, the cursor (the
  hand over the closed paper and over a mark with a link while the drag has
  moved under 4 pixels), the press, the held pointer (recorded for the next
  frame's update and taken), the release;
- the paper's sounds (the sound set `paper`: dragStart paper-dragstart,
  dragStop and drop paper-dragstop, toTop paper-totop) and `toTop` on a
  press, which plays when the paper is already on top (always here: it is
  the only paper);
- the drawing: the drag shadow (the page in black at alpha 0.5, 4 right and
  4 down), the page and its marks, or the closed picture, each cut to its
  clip rectangle (DeskItem.clip, updateClipRects).

Left out (docs/milestone-4.md, 4c): following a link on a click (4d), the
other papers (4e), the tilt draw, the double click (the inspect mode is not
on day 1).
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deskmove  # noqa: E402
import deskpics  # noqa: E402
import fontpage  # noqa: E402
import layout as LAYOUT  # noqa: E402
import pages  # noqa: E402
from PIL import Image  # noqa: E402

L = LAYOUT.DESKTOP
BOOTH_Y = 103
MAX_DT = 0.1
SOUNDS = {"dragStart": "paper-dragstart", "dragStop": "paper-dragstop", "drop": "paper-dragstop",
          "toTop": "paper-totop"}
SHADOW_OFFSET = (4, 4)
SHADOW_ALPHA = 0.5
PAGE = "made/rules-page"
SHADOW = "made/rules-shadow"


def page_mask(assets, rules, confiscation=""):
    """BoothEnv's Rules/PageMask: the <rulebook> pages of Facts.xml whose
    rule is in force (a substring test on the day's rules text) or have
    none, and whose confiscation is the day's or have none; each id
    followed by '-'."""
    # Facts.xml is not well-formed XML (a bare && in a condition), so only
    # its <rulebook> element is cut out and parsed.
    text = open(os.path.join(assets, "data", "Facts.xml"), encoding="utf-8").read()
    part = text[text.index("<rulebook>"):text.index("</rulebook>") + len("</rulebook>")]
    out = ""
    for page in ET.fromstring(part).findall("page"):
        rule, conf = page.get("rule"), page.get("confiscation")
        if rule and rule not in rules:
            continue
        if conf and conf != confiscation:
            continue
        out += page.get("id") + "-"
    return out


class Clock:
    """app.Clock run by whole frames: start() makes the next update give 0;
    an update gives the frames since the last one times DT, at most 0.1 s."""

    def __init__(self, dt):
        self.step, self.started, self.last, self.dt = dt, False, 0, 0.0

    def start(self):
        self.started = False

    def update(self, tick):
        if not self.started:
            self.started, self.dt = True, 0.0
        else:
            self.dt = min(MAX_DT, (tick - self.last) * self.step)
        self.last = tick


class TouchDrag(deskmove.TouchDrag):
    """booth.TouchDrag with its own clock (`tick` is the screen's frame
    count, set by the owner before each frame's calls)."""

    def __init__(self, dt):
        super().__init__()
        self.clock = Clock(dt)
        self.tick = 0

    def start(self, touch):
        super().start(touch)
        self.clock.start()

    def update(self, touch):
        self.clock.update(self.tick)
        super().update(touch)

    def apply_decay(self, pos, dt):
        if self.touching:
            return
        if not self.has_vel():
            self.vel = [0.0, 0.0]
            return
        self.clock.update(self.tick)
        super().apply_decay(pos, self.clock.dt)


def clip_quad(q, clip):
    """Quad.make cut by a clip rectangle (screen coordinates): the quad
    keeps its place and picture piece and draws only the pixels inside the
    clip (fontpage.Quad.clip), which are the pixels the game's
    proportional cut leaves."""
    q.clip = clip
    return q


class Rulebook:
    def __init__(self, assets, lib, pictures, rules, dt, sounds):
        self.lib, self.pictures, self.sounds = lib, pictures, sounds
        paper = [p for p in pages.load(assets) if p.id == "Rules"][0]
        self.paper = paper
        self.mask = page_mask(assets, rules)
        self.nav = pages.Nav(paper, self.mask)
        # Paper.setPage(0): the page picture is a copy; its marker pixels
        # are painted over by the layout.
        page_index = 0
        while not self.nav.has_page(page_index):
            page_index += 1
        image = Image.open(os.path.join(assets, "papers", paper.pages[page_index].image)).convert("RGBA")
        size = pages.literal_image_size(assets)
        self.placed = pages.layout(paper, page_index, image, lib, nav=self.nav, image_size=size)
        for v in self.placed:
            if v.kind == "image":
                name = "papers/" + v.mark.image
                if name not in pictures:
                    pictures[name] = Image.open(os.path.join(assets, name)).convert("RGBA")
        pictures[PAGE] = image
        shadow = image.copy()
        px = shadow.load()
        for y in range(shadow.height):
            for x in range(shadow.width):
                if px[x, y][3] != 0:
                    px[x, y] = (0, 0, 0, 255)
        pictures[SHADOW] = shadow
        outer = Image.open(os.path.join(assets, "papers", "RulesOuter.png")).convert("RGBA")
        pictures["papers/RulesOuter.png"] = outer
        dock = L["dockPoints"]["rules"]
        self.item = deskmove.DeskItem(outer=outer.size, inner=image.size, dock=dock, reveal=("DOCKED",))
        self.item.touch = TouchDrag(dt)
        self.item.start_reveal()
        self.drag_start_stage = None
        self.frame = 0

    # -- the frame

    def _sounds(self, events):
        for e in events:
            if e.startswith("sound "):
                self.sounds.append((self.frame, SOUNDS.get(e[6:], e[6:])))

    def update(self, dt, tick):
        """DeskItem.update: the drag's frame (from the pointer recorded in the
        last react), then the state's."""
        item = self.item
        item.touch.tick = tick
        item.events = []
        if item.dragging:
            item.drag_to(self.drag_cur)
        item.update(dt)
        self._sounds(item.events)
        item.events = []

    def world_rect(self):
        """DeskItem.worldRect in screen coordinates: the shown sprite's hit
        rectangle cut to its clip."""
        item = self.item
        x, y = item.pos[0], item.pos[1] + BOOTH_Y
        r = self.local_clip()
        return (r[0] + x, r[1] + y, r[2], r[3])

    def local_clip(self):
        """The shown sprite's clip rectangle in the item's coordinates."""
        item = self.item
        if item.placement == deskmove.INNER:
            return deskpics.clip_rect(item.pos, (0, 0), item.inner, L["boothInnerClip"])
        return deskpics.clip_rect(item.pos, (0, 0), item.outer, L["boothOuter"])

    def visual_at(self, world):
        """getInnerVisualAt, then getOuterVisualAt: ('mark', Placed),
        ('page', None), ('outer', None) or None."""
        item = self.item
        lx, ly = world[0] - item.pos[0], world[1] - BOOTH_Y - item.pos[1]
        clip = self.local_clip()
        if item.placement == deskmove.INNER:
            page_rect = deskpics.hit_rect((0, 0), item.inner, clip)
            visuals = [(v, deskpics.hit_rect((v.x, v.y), v.size, clip), True) for v in self.placed]
            picked = deskpics.pick_inner_visual((lx, ly), page_rect, visuals)
            if picked is None:
                return None
            return ("page", None) if picked == "page" else ("mark", picked)
        if item.placement == deskmove.OUTER:
            if deskpics.contains(deskpics.hit_rect((0, 0), item.outer, clip), lx, ly):
                return ("outer", None)
        return None

    def react(self, inp, ent):
        """DeskItem.react; `ent` is the item's input identity."""
        item = self.item
        item.events = []
        p = inp.pointer_over(ent, self.world_rect())
        if p is not None:
            cursor = "ARROW"
            at = self.visual_at(p.world)
            if at is not None and at[0] == "outer":
                cursor = "HAND"
            elif at is not None:                 # the page or one of its marks
                has_link = at[0] == "mark" and bool(at[1].mark.link)
                if not item.dragging or deskmove.cheb_floor(p.world, self.drag_start_stage) < deskmove.DRAG_CLICK_DIST:
                    cursor = "HAND" if has_link else "ARROW"
            p.set_cursor(cursor)
            if p.just_down:
                self.start_drag(p.world)
            if p.down:
                self.drag_cur = (p.world[0], p.world[1] - BOOTH_Y)
                p.capture(ent)
        if item.dragging and (p is None or not p.down):
            out = item.end_drag()
            # A click (under 4 pixels): Paper.onClick follows a link (4d).
            del out
        self._sounds(item.events)
        item.events = []

    def start_drag(self, world):
        item = self.item
        mouse = (world[0], world[1] - BOOTH_Y)
        if item.start_drag(mouse):
            self.drag_start_stage = world
            self.drag_cur = mouse
            # The paper is already the last of its parent's children.
            item.events.append("sound toTop")

    # -- drawing

    def draw(self, page):
        """The item's sprites in order (shadow, page, closed picture), then
        the page's marks, each cut to its clip, in screen coordinates."""
        item = self.item
        ox, oy = item.pos[0], item.pos[1] + BOOTH_Y
        quads = []

        def clip_to_screen(c):
            return (c[0] + ox, c[1] + oy, c[2], c[3])

        if item.placement == deskmove.INNER:
            clip = clip_to_screen(self.local_clip())
            if item.shadow:
                sc = deskpics.clip_rect(item.pos, SHADOW_OFFSET, item.inner, L["boothInnerClip"])
                w, h = item.inner
                q = fontpage.Quad(SHADOW, ox + SHADOW_OFFSET[0], oy + SHADOW_OFFSET[1], w, h, (0, 0, w, h),
                                  (1.0, 1.0, 1.0, SHADOW_ALPHA))
                quads.append(clip_quad(q, clip_to_screen(sc)))
            w, h = item.inner
            quads.append(clip_quad(fontpage.Quad(PAGE, ox, oy, w, h, (0, 0, w, h), 0xFFFFFFFF), clip))
            for v in self.placed:
                if v.kind == "image":
                    name = "papers/" + v.mark.image
                    iw, ih = self.pictures[name].size
                    quads.append(clip_quad(fontpage.Quad(name, ox + v.x, oy + v.y, iw, ih, (0, 0, iw, ih),
                                                         0xFFFFFFFF), clip))
                else:
                    tiles, _, _, _ = v.text.build()
                    font = v.text.font
                    for tile in tiles:
                        tw, th = tile.dst[2], tile.dst[3]
                        x, y = ox + v.x + tile.dst[0], oy + v.y + tile.dst[1]
                        if tile.page is None:
                            q = fontpage.Quad(fontpage.WHITE, x, y, tw, th, (0, 0, 1, 1), tile.color)
                        else:
                            q = fontpage.Quad(font.page_files[tile.page], x, y, tw, th, tile.src, tile.color)
                        quads.append(clip_quad(q, clip))
        elif item.placement == deskmove.OUTER:
            clip = clip_to_screen(self.local_clip())
            w, h = item.outer
            quads.append(clip_quad(fontpage.Quad("papers/RulesOuter.png", ox, oy, w, h, (0, 0, w, h),
                                                 0xFFFFFFFF), clip))
        page.quads += [q for q in quads if q is not None]

    def state(self):
        item = self.item
        return {"x": item.pos[0], "y": item.pos[1], "placement": item.placement, "state": item.state,
                "dragging": item.dragging, "shadow": item.shadow}
