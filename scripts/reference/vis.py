"""The rest of app.vis that the port needs (docs/vis-basics.md).

- colours: ColorData (four floats, 0 to 1) to and from the 0xAARRGGBB
  number the pictures use (Color.fromUInt / toUInt);
- the text forms of points and rectangles in the data files
  (Point.parse, Rect.parse), with their odd cases;
- the nine-slice frame (app.vis.Frame): its nine tiles;
- an atlas of chips (app.vis.Atlas.buildTiles): one tile per visible chip,
  in y order;
- Point.transform and Point.distToSeg.
Pure Python.
"""

import math
import re


# ------------------------------------------------------------- colours

def from_uint(u):
    """Color.fromUInt: (r, g, b, a) floats, each channel / 255."""
    return ((u >> 16 & 0xFF) / 255.0, (u >> 8 & 0xFF) / 255.0, (u & 0xFF) / 255.0,
            (u >> 24 & 0xFF) / 255.0)


def to_uint(r, g, b, a):
    """Color.toUInt: each channel held to 0..1, times 255, cut toward zero."""
    c = lambda v: int(min(max(v, 0.0), 1.0) * 255.0)
    return c(b) | c(g) << 8 | c(r) << 16 | c(a) << 24


def pixel_bytes(u):
    """How a 0xAARRGGBB pixel lies in an Image's memory: B, G, R, A."""
    return bytes([u & 0xFF, u >> 8 & 0xFF, u >> 16 & 0xFF, u >> 24 & 0xFF])


# ------------------------------------------------------------- text forms

def parse_float(s):
    """Haxe Std.parseFloat for the forms the data uses: the longest leading
    number; NaN when there is none (assumed from Haxe's documented rule;
    the C# version was not read)."""
    m = re.match(r"\s*[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?", s)
    return float(m.group(0)) if m else float("nan")


def parse_point(text, default=None):
    """Point.parse: split on single spaces; exactly two parts, each trimmed,
    else the default (or (0, 0)). So '10  20' (two spaces) is NOT a point."""
    parts = text.split(" ")
    if len(parts) != 2:
        return default if default is not None else (0.0, 0.0)
    return (parse_float(parts[0].strip()), parse_float(parts[1].strip()))


def parse_rect(text, default=None):
    """Rect.parse: StringUtil.splitAndTrim on ' ' (pieces trimmed, empty
    pieces dropped, so extra spaces are fine here); four parts, else the
    default (or 0, 0, 100, 100)."""
    parts = [p.strip() for p in text.split(" ") if p.strip()]
    if len(parts) != 4:
        return default if default is not None else (0.0, 0.0, 100.0, 100.0)
    return tuple(parse_float(p) for p in parts)


# ------------------------------------------------------------- geometry

def transform(p, m):
    """Point.transform with an affine (m00, m01, m02, m10, m11, m12)."""
    x, y = p
    m00, m01, m02, m10, m11, m12 = m
    return (y * m01 + x * m00 + m02, x * m10 + y * m11 + m12)


def dist_to_seg(a, b, p):
    """Point.distToSeg: distance from p to the segment a..b."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    if l2 == 0.0:
        return math.hypot(p[0] - a[0], p[1] - a[1])
    t = min(1.0, max(0.0, (dx * (p[0] - a[0]) + dy * (p[1] - a[1])) / l2))
    return math.hypot(p[0] - (dx * t + a[0]), p[1] - (dy * t + a[1]))


# ------------------------------------------------------------- frames

def frame_border(image_size, scale9):
    """Frame.get_borderL/R/T/B: the fixed edges around the stretched middle."""
    iw, ih = image_size
    x, y, w, h = scale9
    return {"L": x, "R": iw - (x + w), "T": y, "B": ih - (y + h)}


def frame_outer_from_inner(image_size, scale9, inner):
    """Frame.setInnerRect: the frame's position and outer size for a rect
    that must fit inside the stretched part."""
    b = frame_border(image_size, scale9)
    return (inner[0] - b["L"], inner[1] - b["T"], b["L"] + inner[2] + b["R"],
            b["T"] + inner[3] + b["B"])


def frame_tiles(image_size, scale9, outer_size):
    """Frame.buildTiles: nine (source rect, target rect) pairs, target in the
    frame's own coordinates. Corners keep their size; the edges stretch one
    way, the middle both ways (the standard nine-slice; the column and row
    edges and the source rects read in full, the target assignments in
    outline)."""
    iw, ih = image_size
    sx, sy, sw, sh = scale9
    ow, oh = outer_size
    xs_src = [0, sx, sx + sw, iw]
    ys_src = [0, sy, sy + sh, ih]
    right = ow - (iw - (sx + sw))
    bottom = oh - (ih - (sy + sh))
    xs_dst = [0, sx, right, ow]
    ys_dst = [0, sy, bottom, oh]
    tiles = []
    for row in range(3):
        for col in range(3):
            src = (xs_src[col], ys_src[row], xs_src[col + 1] - xs_src[col],
                   ys_src[row + 1] - ys_src[row])
            dst = (xs_dst[col], ys_dst[row], xs_dst[col + 1] - xs_dst[col],
                   ys_dst[row + 1] - ys_dst[row])
            tiles.append((src, dst))
    return tiles


def frame_apply_border(image_size, scale9, rect):
    """Frame.applyBorder: grow a rectangle by the frame's borders."""
    b = frame_border(image_size, scale9)
    x, y, w, h = rect
    nx, ny = x - b["L"], y - b["T"]
    return (nx, ny, b["L"] + w + b["R"], b["T"] + h + b["B"])


# ------------------------------------------------------------- atlases

def atlas_tiles(chips, scale=1.0):
    """Atlas.buildTiles. chips: dicts with x, y, visible, mirror, color,
    source (x, y, w, h) or None, origin (x, y). Sorted by y (a stable sort
    is assumed; the game uses Array.quicksort, whose tie order was not
    checked). Returns (source, target, mirror, color) per drawn chip."""
    out = []
    for c in sorted(chips, key=lambda c: c["y"]):
        if not c["visible"] or c.get("source") is None:
            continue
        sx, sy, sw, sh = c["source"]
        ox, oy = c["origin"]
        dst = ((c["x"] - ox) * scale, (c["y"] - oy) * scale, sw * scale, sh * scale)
        out.append(((sx, sy, sw, sh), dst, bool(c.get("mirror")), c.get("color")))
    return out


if __name__ == "__main__":
    print(hex(to_uint(*from_uint(0xFF676C54))), pixel_bytes(0xFF676C54))
    print(parse_point("10 20"), parse_point("10  20"), parse_rect("1 2 3 4"))
    for t in frame_tiles((9, 9), (3, 3, 3, 3), (40, 20)):
        print(t)
