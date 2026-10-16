"""Reference for the pictures of a paper on the desk: play.day.booth.DeskItem and
the parts of play.day.booth.Paper that give it pictures (docs/desk-pictures.md).

A paper on the desk is a DeskItem with up to four looks, one shown at a time:
the closed paper on the counter (outer), the open page on the desk (inner),
the paper in the confiscation drawer (filer) and, for a few, the paper hung
on the wall (mount). This script makes those pictures as the code does,
and holds the rules for clipping, picking the mark under the cursor
(PaperInnerVisuals.compareProximity and DeskItem.getInnerVisualAt), the
stamp ink layer, the odd-shape click test, and Image.render (a stretched
tile drawn into a picture).

    python -I scripts/reference/deskpics.py <assets dir> <out dir> [--zoom N]

writes the closed pictures of a few papers at three tilts, a hung picture,
a drawer picture and the dragged page's shadow, as PNG files blown up
--zoom times (4). They are made from the game's art: keep <out dir> in a
gitignored folder.

Not modelled: where the item sits and moves (dragging, the reveal and hide
animations, the drawer), the desktop values of the layout's rectangles
(boothInnerClip, boothOuter, wall; not read), the drawer label's text
(it is drawn by text.py's rules; only its place is given here), and how
the Unity side draws the quads on screen.
"""

import math
import os
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import factpics as FP  # noqa: E402
from faces import Image  # noqa: E402

OVERLAY, BLEND = FP.OVERLAY, FP.BLEND

# Paper constructor: the closed picture's tilt, (r * 60 - 30) degrees
TILT_SPAN_DEG, TILT_LOW_DEG = 60.0, 30.0
# PaperDef.generateRotatedOuterImage
OUTER_SCALE = 0.5                    # the closed picture is drawn at half size
OUTER_SHADOW = 0xFF676C54            # its shadow's colour
OUTER_SHADOW_AT = (-1, 2)            # where the shadow is pasted
# DeskItem
INNER_SHADOW = 0xFF000000            # the dragged page's shadow (createShadow)
INNER_SHADOW_ALPHA = 0.5             # ... drawn at half opacity
INNER_SHADOW_OFFSET = (4.0, 4.0)     # ... 4 pixels right and down
ODD_SHAPE_ALPHA = 8                  # confirmHitTestPointVisible: alpha above this is solid
GIVE_ICON = "assets/GiveIcon.png"
# Paper constructor, the drawer (filer) picture of a confiscatable paper
FILER_ENVELOPE = "assets/papers/FilerEnvelopeOpen.png"
FILER_STRIP_W = 30                   # the strip of the closed picture shown in the envelope
FILER_STRIP_MIN_X = 10.0             # Math.max(10, outer width - 30)
FILER_STRIP_Y = 1
FILER_LABEL_X = 13                   # the label text: x 13, y capHeight - ascent + 2
FILER_LABEL_FONT = "small_tight"
FILER_LABEL_COLOR = 0xFF303030
# Paper constructor, the rack picture (only with a carousel: phone layout)
RACK_SHADOW = 0x80000000
# PaperInnerVisuals.compareProximity
PROX_SAME = 1.0                      # "same height" / "same edge" tolerance
PROX_WIDE = 15.0                     # a rectangle this wide or wider is "wide"
PROX_FACTOR = 0.75
PROX_SHRINK = (-1.0, -1.0, 2.0, 2.0)  # subtracted from (x, y, w, h) each round
PROX_ROUNDS = 5
# Image.render
RENDER_UV_NUDGE = 0.001              # added before the picture coordinates are floored
STRETCH_EPSILON = 0.01               # Visual.renderToImage: a tile is stretched beyond this


def tilt_angle(fraction):
    """The closed picture's turn in radians, from one draw of the booth's
    generator (Rand.random, 0 <= fraction < 1). rotate="false" gives 0
    without a draw."""
    return (fraction * TILT_SPAN_DEG - TILT_LOW_DEG) * math.pi / 180.0


def replace_non_transparent(image, color):
    """Image.replaceNonTransparent: every pixel whose alpha is not 0 becomes
    `color`, alpha included."""
    image.px = [color if p >> 24 else p for p in image.px]
    return image


def create_shadow(image, color):
    """ImageTools.createShadow: a copy with every non-transparent pixel set
    to `color`."""
    return replace_non_transparent(FP.copy(image), color)


def outer_is_turned(paper):
    """generateRotatedOuterImage turns, halves and shadows the closed picture
    unless the paper has a dock point or a wall picture."""
    return paper.get("dock") != "true" and paper.get("mount") is None


def outer_picture(assets, paper, angle):
    """PaperDef.generateRotatedOuterImage(res, angle). `paper` is the
    <paper> element's attributes."""
    outer = FP.load(os.path.join(assets, "assets", "papers", paper["outer"]))
    if not outer_is_turned(paper):
        return outer                   # the shared picture as it is
    turned = FP.transformed(outer, angle, OUTER_SCALE)
    shadow = create_shadow(turned, OUTER_SHADOW)
    # the width rounded up to even, the height plus one rounded up to even
    out = Image(((turned.width + 1) // 2) * 2, ((turned.height + 2) // 2) * 2)
    FP.fill(out, 0)
    FP.paste(out, shadow, OUTER_SHADOW_AT[0], OUTER_SHADOW_AT[1], mode=OVERLAY)
    FP.paste(out, turned, 0, 0, mode=OVERLAY)
    return out


def give_icon_place(outer_w, icon_w, icon_h):
    """DeskItem.setOuterImage: the give icon sits centred over the closed
    picture, its bottom on the picture's top edge."""
    return int(math.floor(outer_w * 0.5 - icon_w * 0.5)), -float(icon_h)


def filer_strip_rect(outer, envelope):
    """The part of the (unturned) closed picture shown in the drawer envelope,
    and where it goes on the envelope."""
    rect = (max(FILER_STRIP_MIN_X, float(outer.width - FILER_STRIP_W)), FILER_STRIP_Y,
            FILER_STRIP_W, min(float(outer.height), float(envelope.height - 2)))
    return rect, (float(envelope.width - 31), 1.0)


def filer_preview(assets, paper):
    """The drawer picture of a confiscatable paper: the open envelope, with a
    strip of the closed picture on it (a separate sprite in the game, drawn
    over the envelope; here pasted with BLEND). The label text is left out."""
    envelope = FP.load(os.path.join(assets, FILER_ENVELOPE))
    outer = FP.load(os.path.join(assets, "assets", "papers", paper["outer"]))
    rect, at = filer_strip_rect(outer, envelope)
    strip = FP.copy(outer, rect)
    out = FP.copy(envelope)
    FP.paste(out, strip, at[0], at[1], mode=BLEND)
    return out


def rack_picture(outer, turned_half):
    """The rack picture (only made with a carousel, so not on desktop): the
    closed picture, halved unless it docks or hangs, on a translucent black
    copy of itself shifted 2 to the left."""
    out = Image(turned_half.width + 2, turned_half.height)
    FP.paste(out, create_shadow(turned_half, RACK_SHADOW), 0, 0)
    FP.paste(out, turned_half, 2, 0, mode=BLEND)
    return out


# ------------------------------------------------------------------ clipping

def clip_rect(item_pos, visual_pos, size, bounds):
    """DeskItem.clip: the visual's rectangle in the item's parent (the booth),
    cut to `bounds` (also in the booth), then moved back into the item's
    own coordinates. A cut that leaves nothing gives a zero width or height."""
    x = visual_pos[0] + item_pos[0]
    y = visual_pos[1] + item_pos[1]
    bx, by, bw, bh = bounds
    left = max(x, bx)
    right = max(left, min(size[0] + x, bw + bx))
    top = max(y, by)
    bottom = max(top, min(size[1] + y, bh + by))
    return (left - item_pos[0], top - item_pos[1], right - left, bottom - top)


def hit_rect(pos, size, clip=None):
    """Visual.hitRect: (x, y, w, h), cut to the clip rectangle when there is one."""
    x, y, w, h = pos[0], pos[1], size[0], size[1]
    if clip is None:
        return (x, y, w, h)
    left = max(x, clip[0])
    right = max(left, min(w + x, clip[2] + clip[0]))
    top = max(y, clip[1])
    bottom = max(top, min(h + y, clip[3] + clip[1]))
    return (left, top, right - left, bottom - top)


def contains(r, px, py, expand=0.0):
    return (r[0] - expand <= px < r[0] + r[2] + expand
            and r[1] - expand <= py < r[1] + r[3] + expand)


def odd_shape_solid(image, x, y):
    """confirmHitTestPointVisible for an odd-shaped page: a point counts only
    if the page picture's pixel there has alpha above 8. Positions are cut
    toward zero; outside the picture is not solid."""
    ix, iy = int(x), int(y)
    if ix < 0 or iy < 0 or ix >= image.width or iy >= image.height:
        return False
    return (image.px[iy * image.width + ix] >> 24) > ODD_SHAPE_ALPHA


# --------------------------------------------------------- picking a mark

def compare_proximity(p, ra, rb):
    """PaperInnerVisuals.compareProximity(p, ra, rb). Negative: ra is the
    better pick for point p; positive: rb; 0: no preference."""
    px, py = p
    if ra == rb:
        return 0
    ax, ay, aw, ah = ra
    bx, by, bw, bh = rb
    # one rectangle inside the other: the inner one wins
    if bh <= ah and ay <= by and bh + by <= ah + ay and bw <= aw and ax <= bx \
            and bx + bw <= ax + aw:
        return 1
    if ah <= bh and by <= ay and ah + ay <= bh + by and aw <= bw and bx <= ax \
            and ax + aw <= bx + bw:
        return -1
    # the same height and a shared left or right edge (within 1): a narrow
    # one beats a wide one unless the point is clearly nearer the wide one's
    # middle line
    if abs(ah - bh) < PROX_SAME and (abs(ax - bx) < PROX_SAME
                                     or abs((aw + ax) - (bw + bx)) < PROX_SAME):
        da = abs(py - int(math.floor(ah * 0.5 + ay)))
        db = abs(py - int(math.floor(bh * 0.5 + by)))
        if aw >= PROX_WIDE:
            if bw < PROX_WIDE and db * PROX_FACTOR < da:
                return 1
        elif bw >= PROX_WIDE and da * PROX_FACTOR < db:
            return -1
    # shrink both by one pixel on every side, up to five times, while the
    # point is in one of them: the first time only one holds it, it wins
    a, b = list(ra), list(rb)
    for _ in range(PROX_ROUNDS):
        for r in (a, b):
            r[0] -= PROX_SHRINK[0]
            r[1] -= PROX_SHRINK[1]
            r[2] -= PROX_SHRINK[2]
            r[3] -= PROX_SHRINK[3]
        in_a, in_b = contains(a, px, py), contains(b, px, py)
        if in_a and not in_b:
            return -1
        if in_b and not in_a:
            return 1
        if not (in_a or in_b):
            break
    # the nearer rectangle (squared distance, 0 inside)
    def dist2(r):
        if contains(r, px, py):
            return 0.0
        cx = min(max(px, r[0]), r[0] + r[2])
        cy = min(max(py, r[1]), r[1] + r[3])
        return (px - cx) ** 2 + (py - cy) ** 2
    d_a, d_b = dist2(ra), dist2(rb)
    if d_a < d_b:
        return -1
    if d_b < d_a:
        return 1
    # the nearer middle (whole-pixel middles, distance |dx| + |dy| floored)
    def middle_dist(r):
        mx = int(math.floor(r[2] * 0.5 + r[0]))
        my = int(math.floor(r[3] * 0.5 + r[1]))
        return int(math.floor(abs(px - mx))) + int(math.floor(abs(py - my)))
    m_a, m_b = middle_dist(ra), middle_dist(rb)
    if m_a < m_b:
        return -1
    if m_b < m_a:
        return 1
    return 0


def pick_inner_visual(p, page_rect, visuals, expand=0.0):
    """DeskItem.getInnerVisualAt, in the item's own coordinates. `page_rect`
    is the page sprite's hit rectangle; `visuals` are (name, hit rectangle,
    visible) in the order they were added. Returns the name of the picked
    visual, "page" when the point is on the page but no visual, or None."""
    if not contains(page_rect, p[0], p[1], expand):
        return None
    best, best_rect = None, None
    for name, rect, visible in visuals:
        if not visible or not contains(rect, p[0], p[1], expand):
            continue
        if best is not None and compare_proximity(p, rect, best_rect) > 0:
            continue
        best, best_rect = name, rect
    return best if best is not None else "page"


# ------------------------------------------------------------ stamp ink

def stamp_ink(ink_layer, ink, local_x, local_y):
    """DeskItem.applyStampInkToInner, after the overlap test: the ink picture
    is pasted (OVERLAY: pixels with alpha 128 or more, as they are) into the
    item's ink layer, a transparent picture the size of the page when the
    first ink landed. Positions are cut toward zero."""
    return FP.paste(ink_layer, ink, local_x, local_y, mode=OVERLAY)


def ink_overlaps(item_x, item_y, inner_w, inner_h, ink_x, ink_y, ink_w, ink_h):
    """The test before stamping: the ink's rectangle and the page's overlap
    (touching edges do not count)."""
    return (ink_x < inner_w + item_x and item_x < ink_w + ink_x
            and ink_y < inner_h + item_y and item_y < ink_h + ink_y)


# ------------------------------------------------------------- Image.render

def render_quad(dst, src, px, py, pr, pb, ux, uy, ur, ub, color=0xFFFFFFFF,
                mode=BLEND, clip_w=None, clip_h=None):
    """Image.render(quad, paste mode): draw part of `src` stretched into the
    rectangle (px, py)-(pr, pb) of `dst`, nearest pixel, tinted by `color`
    (0xAARRGGBB). ux..ub are the source's corners as fractions of its size.
    Modes as Image.paste: REPLACE writes, OVERLAY writes alpha >= 128,
    BLEND mixes. clip_w / clip_h default to the picture's size."""
    cw = dst.width if clip_w is None or clip_w < 0 else clip_w
    ch = dst.height if clip_h is None or clip_h < 0 else clip_h
    x0, y0 = int(math.floor(px)), int(math.floor(py))
    x1, y1 = int(math.floor(pr)), int(math.floor(pb))
    if not (x0 < cw and x1 > 0 and y0 < ch and y1 > 0):
        return dst
    u0 = int(math.floor(src.width * ux + RENDER_UV_NUDGE))
    v0 = int(math.floor(src.height * uy + RENDER_UV_NUDGE))
    u1 = int(math.floor(src.width * ur + RENDER_UV_NUDGE))
    v1 = int(math.floor(src.height * ub + RENDER_UV_NUDGE))

    def idiv(a, b):                    # whole-number division, cut toward zero
        q = abs(a) // abs(b)
        return q if (a >= 0) == (b > 0) else -q
    if x0 < 0:
        u0 += idiv((u0 - u1) * x0, x1 - x0)
        x0 = 0
    if cw < x1:
        u1 += idiv((u1 - u0) * (cw - x1), x1 - x0)
        x1 = cw
    if y0 < 0:
        v0 += idiv((v0 - v1) * y0, y1 - y0)
        y0 = 0
    if ch < y1:
        v1 += idiv((v1 - v0) * (ch - y1), y1 - y0)
        y1 = ch
    if x0 == x1 or y0 == y1:
        return dst
    ta, tr, tg, tb = color >> 24, (color >> 16) & 255, (color >> 8) & 255, color & 255
    du, dv, dw, dh = u1 - u0, v1 - v0, x1 - x0, y1 - y0
    for y in range(y0, y1):
        sy = int((y - y0) * dv / dh + v0)
        for x in range(x0, x1):
            sx = int((x - x0) * du / dw + u0)
            p = src.px[sx + src.width * sy]
            a = ((p >> 24) * ta) // 255
            r = (((p >> 16) & 255) * tr) // 255
            g = (((p >> 8) & 255) * tg) // 255
            b = ((p & 255) * tb) // 255
            i = dst.width * y + x
            if i < 0 or i >= len(dst.px):
                continue
            if mode == FP.REPLACE:
                dst.px[i] = (a << 24) | (r << 16) | (g << 8) | b
            elif mode == OVERLAY:
                if a > 0x7F:
                    dst.px[i] = (a << 24) | (r << 16) | (g << 8) | b
            else:
                q = dst.px[i]
                keep = 255 - a
                nr = (r * a + ((q >> 16) & 255) * keep) // 255
                ng = (g * a + ((q >> 8) & 255) * keep) // 255
                nb = (b * a + (q & 255) * keep) // 255
                dst.px[i] = (max(q >> 24, a) << 24) | (nr << 16) | (ng << 8) | nb
    return dst


# --------------------------------------------------------------------- demo

def papers(assets):
    root = ET.parse(os.path.join(assets, "assets", "data", "Papers.xml")).getroot()
    return [dict(p.attrib) for p in root.findall("paper")]


def demo(assets, out_dir, zoom=4):
    os.makedirs(out_dir, exist_ok=True)
    by_id = {}
    for p in papers(assets):
        by_id.setdefault(p["id"], p)
    written = []

    def save(image, name):
        big = Image(image.width * zoom, image.height * zoom)
        for y in range(big.height):
            row = (y // zoom) * image.width
            big.px[y * big.width:(y + 1) * big.width] = [
                image.px[row + x // zoom] for x in range(big.width)]
        path = os.path.join(out_dir, name)
        big.save(path)
        written.append((name, image.width, image.height))

    for pid in ("EntryPermit", "Passport", "IdCard", "TimeBomb", "Rules"):
        paper = by_id[pid]
        fractions = (0.0, 0.5, 0.999) if paper.get("rotate") != "false" else (0.5,)
        for f in fractions:
            angle = tilt_angle(f) if paper.get("rotate") != "false" else 0.0
            save(outer_picture(assets, paper, angle),
                 "outer_%s_%03d.png" % (pid, int(round(f * 1000))))
    plaque = by_id["PlaqueOne"]
    save(FP.load(os.path.join(assets, "assets", "papers", plaque["mount"])), "mount_PlaqueOne.png")
    save(filer_preview(assets, by_id["Passport"]), "filer_Passport.png")
    inner = FP.load(os.path.join(assets, "assets", "papers", "EntryPermitInner.png"))
    shadow = create_shadow(inner, INNER_SHADOW)
    save(shadow, "inner_shadow_EntryPermit.png")
    return written


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    zoom = 4
    if "--zoom" in argv:
        zoom = int(argv[argv.index("--zoom") + 1])
    for name, w, h in demo(argv[1], argv[2], zoom):
        print("%-34s %3d x %3d" % (name, w, h))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
