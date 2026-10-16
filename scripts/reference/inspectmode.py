"""The inspect mode: play.day.booth.InspectUi and its helpers, desktop only.

See docs/inspect-mode.md. This holds:
- which fact path a mark gives (BoothEnv.getFactPathForInnerVisual),
- the two selection slots (InspectUi.selectInspectable) and quick inspect,
- the text shown for a pair (updateOverlay),
- where the open and close buttons and the hint are for a reveal amount,
- the diagram's timeline and which side its label goes on
  (InspectUiDiagram.set_visibleT and the side choice of set).
Pure Python; run it for a short demo.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as LAYOUT  # noqa: E402

L = LAYOUT.DESKTOP

FILL_COLOR = 0x80191212   # InspectUi.kFillColor: the overlay
LINE_COLOR = 0xFFE0E9C7   # kLineColor
RED_COLOR = 0xFFB42B2B    # kRedColor

CLOSED_INTERP = 0.1       # state "closed": blend time
OPEN_INTERP = 0.25        # state "open"
DIAGRAM_OFF_INTERP = 0.25
DIAGRAM_ON_INTERP = 2.0

BOOTH_INSPECTABLES = [    # Booth constructor: fact path, layout rectangle
    ("Booth/Counter", "inspectableCounter"),
    ("Booth/Face", "inspectableFace"),
    ("Booth/Clock", "inspectableClock"),
    ("Booth/Weight", "inspectableWeight"),
]


def lerp_scale(v, in_min, in_max, out_min, out_max):
    v = max(min(v, in_max), in_min)
    return (v - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


# ------------------------------------------------------------- fact paths

def fact_path_for_mark(paper_id_with_index, mark, rules=None, remap=None,
                       transcript_paths=None):
    """getFactPathForInnerVisual. mark: dict with 'fact' (the proxied fact id,
    or None), 'inspectable' (bool), 'link' (or None). Returns the path; the
    paper's own id means 'the paper itself'."""
    if mark is None:
        return paper_id_with_index
    fact = mark.get("fact")
    if not fact or not mark.get("inspectable", True) or mark.get("link"):
        return paper_id_with_index
    if paper_id_with_index == "Transcript":
        i = fact.find("Speech")
        if i < 0:
            return ""
        tail = fact[i + len("Speech"):]
        n = int(tail) if tail.lstrip("-").isdigit() else 0
        if n < 0:
            return ""
        paths = transcript_paths or []
        return paths[n] if n < len(paths) else ""
    rules = rules or {}
    remap = remap or {}
    if fact in rules:
        fact = rules[fact]
    elif fact in remap:
        fact = remap[fact]
    return paper_id_with_index + "/" + fact


class Inspectable:
    def __init__(self, fact_path, rect, selectable=True):
        self.fact_path = fact_path
        self.rect = rect
        self.selectable = selectable

    def is_parent_of(self, other):
        return other.fact_path.startswith(self.fact_path + "/")

    def __repr__(self):
        return "Inspectable(%r)" % self.fact_path


# ------------------------------------------------------------- selection

class Selection:
    """InspectUi.selectedInspectables (two slots) and selectedInspectableAddAtZero."""

    def __init__(self):
        self.slots = [None, None]
        self.add_at_zero = True

    def clear(self):
        """The closed state's function at the end of the blend."""
        self.slots = [None, None]
        self.add_at_zero = True

    def select(self, item):
        """selectInspectable. Returns the sound name, or None."""
        if item is None or not item.selectable:
            return None
        for i, s in enumerate(self.slots):
            if s is not None and s.fact_path == item.fact_path:
                self.slots[i] = None
                return "inspect-unhighlight"
        for i, s in enumerate(self.slots):
            if s is not None and (s.is_parent_of(item) or item.is_parent_of(s)):
                self.slots[i] = None
        if self.slots[0] is None:
            self.slots[0] = item
            self.add_at_zero = False
        elif self.slots[1] is None:
            self.slots[1] = item
            self.add_at_zero = True
        else:
            index = 0 if self.add_at_zero else 1
            self.slots[index] = item
            self.add_at_zero = not self.add_at_zero
        return "inspect-highlight"


def quick_inspect(is_open, selectable):
    """InspectUi.quickInspect (a double click): what happens."""
    if is_open and not selectable:
        return "close"
    if selectable and not is_open:
        return "open and select"
    return "nothing"


# ------------------------------------------------------------- the pair's text

def relationship_text_id(relationship, cleared=False):
    """updateOverlay: the Text.xml id shown for the two selected facts."""
    if relationship == "NONE":
        return "booth_nocorrelation"
    if relationship == "AGREE":
        return "booth_cleared" if cleared else "booth_matching"
    return "booth_discrepancy"


def interrogate_enabled(relationship, has_interrogate_ops):
    """The diagram's 'on' state, on entering: the button works only for a
    disagreement whose invalidating operation has Interrogate responses."""
    return relationship == "DISAGREE" and has_interrogate_ops


# ------------------------------------------------------------- reveal

def reveal_positions(t, open_w, open_h, close_w, close_h, text_w, text_h):
    """InspectUi.set_revealT with the hint at the bottom (desktop): the
    positions of the hint, the open button and the close button for t."""
    bw, bh = L["booth"][2], L["booth"][3]
    start = bw - open_w
    text_x = math.floor(t ** 2 * (((bw - text_w) - open_w) - start) + start)
    text_y = bh - text_h
    e = 1.0 - (1.0 - t) ** 2
    open_x = (bw - (bw - open_w)) * e + (bw - open_w)
    open_y = (bh - (bh - open_h)) * e + (bh - open_h)
    close_x = ((bw - close_w) - bw) * e + bw
    close_y = ((bh - close_h) - bh) * e + bh
    return {
        "hint": (text_x, text_y, t > 0.0),
        "open": (open_x, open_y, t < 1.0),
        "close": (close_x, close_y, t > 0.0),
    }


# ------------------------------------------------------------- the diagram

def diagram_parts(visible_t):
    """InspectUiDiagram.set_visibleT: how far lines 0 and 1, line 2, the
    text and the interrogate button are, for visibleT (0 to 1 over 2 s)."""
    a = lerp_scale(visible_t, 0.0, 0.4, 0.0, 1.0)
    b = lerp_scale(visible_t, 0.4, 0.6, 0.0, 0.999)
    c = lerp_scale(visible_t, 0.6, 1.0, 0.0, 1.0)
    return {
        "line0": lerp_scale(a, 0.0, 0.5, 0.0, 1.0),
        "line1": lerp_scale(a, 0.0, 0.5, 0.0, 1.0),
        "line2": lerp_scale(a, 0.5, 1.0, 0.0, 1.0),
        "text": math.fmod(b * 3.0, 1.0) > 0.5,
        "button": c,
    }


def join_side(r0, r1, text_w, text_h, favor_up_right=False, allow_inner=False):
    """The side choice of InspectUiDiagram.set (before the stable-side memory)."""
    tw = text_w + 4.0
    room = tw + 20.0
    if r1[0] + r1[2] < r0[0]:
        gap_x = r0[0] - (r1[0] + r1[2])
    elif r0[0] + r0[2] < r1[0]:
        gap_x = r1[0] - (r0[0] + r0[2])
    else:
        gap_x = 0.0
    if r1[1] + r1[3] < r0[1]:
        gap_y = r0[1] - (r1[1] + r1[3])
    elif r0[1] + r0[3] < r1[1]:
        gap_y = r1[1] - (r0[1] + r0[3])
    else:
        gap_y = 0.0
    if tw < gap_x:
        return "H"
    if text_h + 4.0 < gap_y:
        mid0 = math.floor(r0[2] * 0.5 + r0[0])
        mid1 = math.floor(r1[2] * 0.5 + r1[0])
        if tw < abs(mid0 - mid1):
            return "V"
    bw, bh = L["booth"][2], L["booth"][3]
    left_blocked = min(r0[0], r1[0]) <= room
    right_blocked = bw - room <= max(r0[0] + r0[2], r1[0] + r1[2])
    top_blocked = min(r0[1], r1[1]) <= 50.0
    bottom_blocked = bh - 50.0 <= max(r0[1] + r0[3], r1[1] + r1[3])
    if gap_y < gap_x:
        if not favor_up_right:
            order = [("T", top_blocked), ("B", bottom_blocked), ("L", left_blocked), ("R", None)]
        else:
            order = [("T", top_blocked), ("B", bottom_blocked), ("R", right_blocked), ("L", None)]
        for side, blocked in order:
            if not blocked:
                return side
    if not favor_up_right:
        if not left_blocked:
            return "L"
        if not right_blocked:
            return "R"
    else:
        if not right_blocked:
            return "R"
        if not left_blocked:
            return "L"
    if not top_blocked:
        return "T"
    if not bottom_blocked or not allow_inner:
        return "B"
    return "I"


def main(argv):
    s = Selection()
    a = Inspectable("Passport/Name", (10, 10, 50, 8))
    b = Inspectable("EntryPermit/Name", (200, 10, 50, 8))
    c = Inspectable("Passport", (0, 0, 130, 162))
    for item in (a, b, c, a):
        print("select %-18s -> %-20s slots %s" % (item.fact_path, s.select(item), s.slots))
    for t in (0.0, 0.2, 0.4, 0.5, 0.6, 0.8, 1.0):
        print("diagram t %.1f" % t, diagram_parts(t))
    print("side for two facts far apart:", join_side((200, 20, 60, 8), (400, 150, 60, 8), 60, 22))


if __name__ == "__main__":
    main(sys.argv)
