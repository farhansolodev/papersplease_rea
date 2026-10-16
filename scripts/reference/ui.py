"""The rest of play.ui (docs/ui-parts.md).

- DiagramLine: a polyline with rounded corners, drawn as single pixels
  two apart (a dotted line), shown up to a fraction of its dots;
- DottedLine: a straight dotted line out of a 32-pixel strip;
- SpeechBubble: the size and place of the box and text for a line, how
  long it stays, and how it opens and closes;
- KineticScroll: dragging with a rubber band and coasting.
Pure Python (the bubble's text width comes from fonts.py when given).
"""

import math


def math_round(x):
    """Haxe Math.round as compiled (same as factpics.math_round)."""
    i = int(x)
    d = x - i
    if d >= 1.0 or -1.0 >= d:
        return i
    if d >= 0.5:
        return i + 1
    if -0.5 > d:
        return i - 1
    return i


def lerp_scale(v, in_min, in_max, out_min, out_max):
    v = max(min(v, in_max), in_min)
    return (v - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


# ------------------------------------------------------------- DiagramLine

def _far(last, x, y):
    """A new dot is added only when it is more than 1 pixel away in x or y."""
    return abs(last[0] - math_round(x)) > 1.0 or abs(last[1] - math_round(y)) > 1.0


def add_dotted_to(dots, p):
    """DiagramLine.addDottedTo: walk from the last dot to p in ceil(length)
    steps, adding a rounded dot whenever it is far enough; then p itself."""
    start = dots[-1]
    d = math.hypot(start[0] - p[0], start[1] - p[1])
    n = int(math.ceil(d))
    for k in range(n):
        t = k / n
        x = (p[0] - start[0]) * t + start[0]
        y = (p[1] - start[1]) * t + start[1]
        if _far(dots[-1], x, y):
            dots.append((float(math_round(x)), float(math_round(y))))
    if _far(dots[-1], p[0], p[1]):
        dots.append((float(math_round(p[0])), float(math_round(p[1]))))


def build_dots(points, corner_radius=10.0):
    """DiagramLine.buildDots: points are floored when added (addPoint)."""
    pts = [(float(math.floor(x)), float(math.floor(y))) for x, y in points]
    dots = [pts[0]]
    prev = pts[0]
    for i in range(1, len(pts) - 1):
        q, r = pts[i], pts[i + 1]
        d1sq = (prev[0] - q[0]) ** 2 + (prev[1] - q[1]) ** 2
        d2 = math.hypot(q[0] - r[0], q[1] - r[1])
        if d1sq != 0.0:
            d1 = math.sqrt(d1sq)
            ux, uy = (q[0] - prev[0]) / d1, (q[1] - prev[1]) / d1
            rad = min(corner_radius, d1)
            if d2 != 0.0:
                rad = min(rad, d2)
            cx, cy = (d1 - rad) * ux + prev[0], (d1 - rad) * uy + prev[1]
            add_dotted_to(dots, (cx, cy))
            if d2 != 0.0:
                n = int(rad + rad)
                vx, vy = (r[0] - q[0]) / d2, (r[1] - q[1]) / d2
                for k in range(1, n + 1):
                    a = math.pi * 0.5 * (k / n)
                    across = (1.0 - math.cos(a)) * rad
                    along = math.sin(a) * rad
                    x = across * vx + cx + along * ux
                    y = across * vy + cy + along * uy
                    if _far(dots[-1], x, y):
                        dots.append((float(math_round(x)), float(math_round(y))))
        prev = q
    add_dotted_to(dots, pts[-1])
    return dots


def visible_dots(dots, visible_t):
    """buildTiles: the first floor(count x visibleT) dots have the colour's
    alpha, the rest alpha 0."""
    return dots[:int(math.floor(len(dots) * visible_t))]


# ------------------------------------------------------------- DottedLine

def dotted_line_tiles(p0, p1, strip=32):
    """DottedLine.set: a horizontal line (when |dy| < 1) or a vertical one,
    made of pieces of a 32-pixel strip with every other pixel set, each
    piece up to 30 long, starting the strip at the piece's parity."""
    if abs(p0[1] - p1[1]) < 1.0:
        a, b = int(math.floor(min(p0[0], p1[0]))), int(math.floor(max(p0[0], p1[0])))
        horizontal = True
    else:
        a, b = int(math.floor(min(p0[1], p1[1]))), int(math.floor(max(p0[1], p1[1])))
        horizontal = False
    tiles = []
    x = a
    while x < b:
        e = min(x + strip - 2, b)
        src_start = x & 1
        if horizontal:
            tiles.append(((src_start, 0, e - x, 1), (x, p0[1], e - x, 1)))
        else:
            tiles.append(((0, src_start, 1, e - x), (p0[0], x, 1, e - x)))
        x = e
    return tiles


def dotted_pixels(p0, p1):
    """The pixels a DottedLine lights: every other pixel from an even one."""
    out = []
    for src, dst in dotted_line_tiles(p0, p1):
        if dst[3] == 1:
            for k in range(int(dst[2])):
                if (src[0] + k) % 2 == 0:
                    out.append((dst[0] + k, dst[1]))
        else:
            for k in range(int(dst[3])):
                if (src[1] + k) % 2 == 0:
                    out.append((dst[0], dst[1] + k))
    return out


# ------------------------------------------------------------- SpeechBubble

PADDING = 4          # SpeechBubble.kPadding
LINE_HEIGHT = 14.0   # kLineHeight (not used below)
BUBBLE_PICTURE = "assets/SpeechBubble.png"
BUBBLE_MIDDLE = (2, 2, 14, 14)
TEXT_COLOR = 0xFF34353F
DOT_COLOR = 0xFFEDE0D8


def bubble_layout(text_w, text_h, align="LEFT", font_cap=0, font_ascent=0):
    """showText: the box (x relative to the bubble, width, height) and the
    text's place. text_w, text_h: the label's size after wrapping."""
    w, h = text_w + 8, text_h + 8
    if align == "LEFT":
        box_l = 0.0
    elif align == "CENTER":
        box_l = float(int(w * -0.5))
    else:
        box_l = -float(w)
    return {"box": (box_l, 0.0, w, h), "box_r": box_l + text_w + 8,
            "text": (box_l + 4, float(font_cap - font_ascent + 5))}


def bubble_wrap_width(single_line_width):
    """showText: no wrapping if the line is at most 160 pixels wide, else 120."""
    return 0 if single_line_width < 161 else 120


def bubble_duration(text):
    """showText: how long the 'on' state lasts, 0.1 s per character."""
    return len(text) * 0.1


def bubble_reveal_parts(t, opening, centred):
    """set_revealT: (dotted line, box width, bounce) amounts for revealT t.
    The state blends: on 0.75 s, off 0.5 s. Without the dotted line (not
    centred) t is first mapped to 0.25..1, which skips the line."""
    if not centred:
        t = lerp_scale(t, 0.0, 1.0, 0.25, 1.0)
    line = lerp_scale(t, 0.0, 0.25, 0.0, 1.0)
    if opening:
        width = lerp_scale(t, 0.25, 0.375, 0.0, 1.0)
        bounce = lerp_scale(t, 0.375, 0.5, 0.0, 1.0)
    else:
        width = lerp_scale(t, 0.25, 0.75, 0.0, 1.0)
        bounce = lerp_scale(t, 0.75, 1.0, 0.0, 1.0)
    return line, width, bounce


def bubble_box_width(box_l, box_r, width_t, bounce_t, min_w):
    """setBoxReveal: the box's width for a reveal (a sine bounce of up to
    5 pixels on top), never less than the frame's borders."""
    bounce = lerp_scale(math.sin(math.pi * bounce_t), 0.0, 1.0, 0.0, 5.0)
    w = int(math.floor((box_r - box_l) * width_t + bounce))
    return int(math.floor(max(min_w, w)))


# ------------------------------------------------------------- KineticScroll

class KineticScroll:
    """play.ui.KineticScroll, one axis. scroll is the content's offset."""

    def __init__(self, decay=0.75):
        self.decay = decay
        self.vel = 0.0
        self.touch = None
        self.last_touch_frame = -10

    def drag(self, frame, touch, scroll, lo, hi):
        """Called on frames while the pointer is down."""
        just = self.last_touch_frame < frame - 1
        if just:
            self.touch = touch
            self.vel = 0.0
        d = max(-100.0, min(100.0, touch - self.touch))
        self.vel = -d * 60.0
        new = scroll - d
        if new < lo:
            out = lo if (lo - new < 1.0 or just) else (new if d < 0 else scroll - d * 0.1)
        elif new > hi:
            out = hi if (new - hi < 1.0 or just) else (new if d > 0 else scroll - d * 0.1)
        else:
            out = new
        self.touch = touch
        self.last_touch_frame = frame
        return out

    def update(self, frame, scroll, lo, hi, dt):
        """Called every frame; coasts and springs back when not touched."""
        if frame - 1 <= self.last_touch_frame:
            return scroll
        new = dt * self.vel + scroll
        if new < lo or new > hi:
            edge = lo if new < lo else hi
            if abs(edge - new) < 1.0:
                self.vel = 0.0
                return edge
            pull = (edge - new) * 0.2
            out = max(new + pull, lo - 100.0) if new < lo else min(new + pull, hi + 100.0)
            self.vel *= self.decay ** 2
            return out
        self.vel *= self.decay ** (60.0 * dt) if dt else 1.0
        return new


if __name__ == "__main__":
    dots = build_dots([(10, 10), (60, 10), (60, 40)])
    print(len(dots), dots[:6], dots[-3:])
    print(dotted_pixels((0, 5), (10, 5)))
    print(bubble_layout(100, 22, "CENTER"), bubble_duration("Papers, please."))
