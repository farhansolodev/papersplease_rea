"""How a paper on the desk moves: play.day.booth.DeskItem, desktop only.

See docs/desk-movement.md. This holds, frame by frame:
- the reveal animations (from the slot, printed from the bottom or top,
  spat from the right, and the instant ones),
- the hide animations (off the bottom or left, into the drawer),
- dragging: which placement the cursor gives (counter, desk, drawer, wall),
  where the paper goes, the clamps, the give icon; dropping; clicks,
- what a paper does when let go: falling to the counter's floor, sliding
  on the desk, settling in the drawer, going back to its dock, being given,
- the dock points' drag clamp and return path, and the drag velocity.

All positions are in booth coordinates (layout.py). Desktop has no
carousel and no multitouch, so those branches are left out. No random
draws happen here. Pure Python; run it for a demo of a few animations.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import layout as LAYOUT  # noqa: E402

L = LAYOUT.DESKTOP

# DeskItem's static values (the .cctor)
HIDE_COUNTDOWN = 1.0      # kHideCountdownMax (set by startHideAnim, not used by the hide itself)
PRINT_COUNTDOWN = 3.0     # kPrintCountdownMax
PRINT_DELAY = 3.0         # kPrintDelay
SPIT_COUNTDOWN = 0.5      # kSpitCountdownMax
DRAG_CLICK_DIST = 4.0     # kDragClickDist
MOUNT_DROP_SINK = 2.0     # kMountDropSink

OUTER, INNER, FILER, MOUNT = "OUTER", "INNER", "FILER", "MOUNT"
NONE, REVEALING, NORMAL, RETURNINGTODOCK, HIDING, HIDDEN, GIVING, GIVEN = (
    "NONE", "REVEALING", "NORMAL", "RETURNINGTODOCK", "HIDING", "HIDDEN", "GIVING", "GIVEN")
GIVE_NO, GIVE_YES_NOW, GIVE_YES_WAITING = "NO", "YES_NOW", "YES_WAITING"


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
    """app.Num.lerpScale: the input held between in_min and in_max, then mapped."""
    v = max(min(v, in_max), in_min)
    return (v - in_min) / (in_max - in_min) * (out_max - out_min) + out_min


def cheb_floor(a, b):
    """max(floor|dx|, floor|dy|) as whole numbers: the game's 'moved' distance."""
    return max(int(math.floor(abs(a[0] - b[0]))), int(math.floor(abs(a[1] - b[1]))))


def inside(r, x, y):
    return r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]


# ------------------------------------------------------------- touch drag

class TouchDrag:
    """booth.TouchDrag: the velocity of a drag, and the slide after it."""

    def __init__(self, decay=0.75):
        self.vel = [0.0, 0.0]
        self.touching = False
        self.touch = [0.0, 0.0]
        self.decay = decay

    def start(self, touch):
        self.touch = list(touch)
        self.vel = [0.0, 0.0]
        self.touching = True

    def update(self, touch):
        """Per frame while dragging: velocity in pixels per second, smoothed by half."""
        dx, dy = touch[0] - self.touch[0], touch[1] - self.touch[1]
        self.touch = list(touch)
        self.vel[0] += (dx * 60.0 - self.vel[0]) * 0.5
        self.vel[1] += (dy * 60.0 - self.vel[1]) * 0.5

    def stop(self):
        self.touching = False

    def has_vel(self):
        return self.vel[0] ** 2 + self.vel[1] ** 2 >= 1.0

    def apply_decay(self, pos, dt):
        """Slide pos by the velocity, which shrinks to 0.75 of itself per 1/60 s."""
        if self.touching:
            return
        if not self.has_vel():
            self.vel = [0.0, 0.0]
            return
        k = 1.0 if dt == 0 else self.decay ** (60.0 * dt)
        self.vel = [self.vel[0] * k, self.vel[1] * k]
        pos[0] = math_round(pos[0] + self.vel[0] * dt)
        pos[1] = math_round(pos[1] + self.vel[1] * dt)


# ------------------------------------------------------------- dock points

def dock_clamp_drag(dock, center, w, h):
    """data.DockPoint.clampDrag for entry TOP, on the closed paper's middle."""
    home, clamp = dock["home"], dock["clamp"]
    hw, hh = w * 0.5, h * 0.5
    cx, cy = center
    if clamp[1] + clamp[3] < cy + hh:              # the bottom is below the clamp
        if home[0] <= cx <= home[0] + home[2]:
            mid = math.floor(home[2] * 0.5 + home[0])
            t = lerp_scale(abs(cx - mid) / hw, 0.5, 1.0, 0.0, 1.0)
            cx = int(mid)
            cy = min(cy, -hh * t + int(math.floor(home[3] * 0.5 + home[1])))
        else:
            cy = clamp[1] + clamp[3] - hh
    cx = min(clamp[0] + clamp[2] - hw, max(clamp[0] + hw, cx))
    cy = min(clamp[1] + clamp[3] - hh, max(clamp[1] + hh, cy))
    return cx, cy


def dock_return_home(dock, x, y, dt, drop_vel, drop_accel):
    """data.DockPoint.returnHome for entry TOP: up above the home, across to
    it at 500 px/s, then down into it with gravity. Returns x, y, landed, drop_vel."""
    home = dock["home"]
    step = dt * 500.0
    landed = False
    if home[1] < y:
        y -= step
        if y <= home[1]:
            y = home[1] - 1.0
    elif abs(x - home[0]) > 0.001:
        if x < home[0] - 0.1:
            x = min(step + x, home[0])
        elif home[0] + 0.1 < x:
            x = max(x - step, home[0])
    elif y < home[1]:
        y += max(1.0, dt * (drop_vel + drop_accel))
        drop_vel += drop_accel
        if not (y < home[1]):
            landed = True
            y = home[1]
    return x, y, landed, drop_vel


# ------------------------------------------------------------- the drawer

class Filer:
    """The parts of booth.Filer that a desk item uses (the drawer)."""

    def __init__(self, back_w=190.0, back_h=210.0, shift_y=0.0):
        self.back_w = back_w                      # assets/Filer.png is 190 x 210
        self.open = False
        self.shift_y = shift_y                    # 5 with the big handle; 0 on desktop
        self.open_h = back_h + shift_y
        self.closed_h = shift_y + 8.0
        self.items = []                            # desk items in the drawer, in child order

    def pos_y(self, t):
        """The drawer's y for openT t (0 closed, 1 open)."""
        base = L["filer"][1]
        return (base - self.closed_h) + t * ((base - self.open_h) - (base - self.closed_h))

    def slot_pos(self, item):
        """getLocalSlotPos: (3, 20 + shiftY + 10 x the number of drawer items before it),
        in the drawer's own coordinates."""
        n = 0
        for other in self.items:
            if other is item:
                break
            if other.placement == FILER:
                n += 1
        return (3.0, n * L["filerEnvelopeSpacingY"] + self.shift_y + 20.0)


# ------------------------------------------------------------- the desk item

class DeskItem:
    def __init__(self, outer, inner, filer_size=None, mount=None, dock=None,
                 filer_type="NONE", reveal=("FROMSLOT",), hide="OFFBOTTOM", filer=None):
        self.outer = list(outer)            # closed size
        self.inner = list(inner)            # open page size
        self.filer_size = list(filer_size) if filer_size else None
        self.mount = list(mount) if mount else None
        self.dock = dock
        self.filer_type = filer_type        # NONE, CANFILER, ONLYFILER
        self.reveal = reveal
        self.hide = hide
        self.filer = filer
        self.pos = [0.0, 0.0]
        self.placement = OUTER
        self.state = NONE
        self.visible = True
        self.drop_vel = 0.0
        self.anim = 0.0
        self.dragging = False
        self.moved = False
        self.was_dragged = False
        self.drag_offset = [0.0, 0.0]
        self.drag_start = [0.0, 0.0]
        self.drag_cur = [0.0, 0.0]
        self.drag_start_placement = OUTER
        self.give_icon = False
        self.shadow = False
        self.put_in_filer_once = False
        self.removed_from_filer_once = False
        self.pos_in_filer = [0.0, 20.0]
        self.touch = TouchDrag()
        self.giveable = lambda item: GIVE_NO
        self.events = []

    def size(self, placement=None):
        p = placement or self.placement
        return {OUTER: self.outer, INNER: self.inner, FILER: self.filer_size or self.inner,
                MOUNT: self.mount}[p]

    def set_placement(self, p):
        if self.filer is None and p == FILER:
            p = INNER
        self.placement = p
        self.shadow = False
        self.give_icon = False

    # -- the clamps

    def clamp(self):
        """clampPlacementPos."""
        x, y = self.pos
        if self.placement == INNER:
            r = L["boothInnerClamp"]
            mx = 70.0 if self.inner[0] >= 70.0 else self.inner[0]
            my = 30.0 if self.inner[1] >= 30.0 else self.inner[1]
            x = min(max(x, r[0] - self.inner[0] + mx), r[0] + r[2] - mx)
            y = min(max(y, r[1] - self.inner[1] + my), r[1] + r[3] - my)
        elif self.placement == OUTER:
            r = L["boothOuterClamp"]
            right = self.outer[0] * 0.5 if L["boothLayout"] == "OUTER_LEFT" else self.outer[0]
            x = min(max(x, r[0]), r[0] + r[2] - right)
            y = min(max(y, r[1]), r[1] + r[3] - self.outer[1] * 0.5)
        elif self.placement == MOUNT:
            r = L["wallMountArea"]
            mw, mh = self.mount
            x = min(max(x, r[0] - mw * 0.5), r[0] + r[2] - mw * 0.5)
            y = min(max(y, r[1] - mh * 0.5), r[1] + r[3] - 10.0)
        self.pos = [x, y]

    # -- revealing

    def start_reveal(self, mount_pos=None):
        """startRevealAnim (no carousel)."""
        self.state = REVEALING
        self.drop_vel = 0.0
        self.visible = True
        kind = self.reveal[0]
        desk = L["desk"]
        mid_x = lambda w: float(int(math.floor(int(math.floor(desk[2] * 0.5 + desk[0])) - w * 0.5)))
        if kind == "DOCKED":
            home = self.dock["home"]
            self.pos = [home[0], home[1]]
            self.set_placement(OUTER)
        elif kind == "FROMSLOT":
            sc = L["slotCenter"]
            self.pos = [float(int(math.floor(sc[0] - self.outer[0] * 0.5))), sc[1] - self.outer[1]]
            self.set_placement(OUTER)
            self.events.append("sound dragStart")
        elif kind == "PRINTBOTTOM":
            self.pos = [mid_x(self.inner[0]), L["boothPrintBottomY"]]
            self.anim = PRINT_COUNTDOWN + PRINT_DELAY
            self.set_placement(INNER)
        elif kind == "SPITFROMRIGHT":
            self.pos = [desk[0] + desk[2], desk[1] + 80.0]
            self.anim = SPIT_COUNTDOWN
            self.set_placement(INNER)
        elif kind == "ONDESK":
            self.pos = [desk[0] + self.reveal[1], desk[1] + self.reveal[2]]
            self.set_placement(INNER)
            self.clamp()
        elif kind == "INFILER":
            sx, sy = self.filer.slot_pos(self)
            self.pos_in_filer = [sx, sy]
            self.pos = [L["filer"][0] + sx, self.filer.pos_y(0.0) + sy]
            self.set_placement(FILER)
        elif kind == "PRINTTOP":
            self.pos = [mid_x(self.inner[0]), desk[1] - self.inner[1]]
            self.anim = PRINT_COUNTDOWN
            self.set_placement(INNER)
            self.events.append("sound photo-print")
        elif kind == "ONWALL":
            self.pos = list(mount_pos)
            self.set_placement(MOUNT)
            self.clamp()

    def animate_reveal(self, dt):
        kind = self.reveal[0]
        desk = L["desk"]
        if kind == "FROMSLOT":
            floor_y = L["outerFloorMidY"] - self.outer[1] * 0.5
            self.pos[1] = min(floor_y, dt * 350.0 + self.pos[1])
            if floor_y <= self.pos[1]:
                self.state = NORMAL
                self.events.append("sound drop")
        elif kind == "PRINTBOTTOM":
            p = max(0.0, 1.0 - self.anim / PRINT_COUNTDOWN)
            p2 = max(0.0, 1.0 - (self.anim - dt) / PRINT_COUNTDOWN)
            h = self.inner[1]
            bottom = L["boothPrintBottomY"]
            start_y = bottom - (h - 20.0)
            if p < 0.8:
                lines = int((h - 1.0) / 20.0)
                n = int(p / 0.8 * lines)
                frac = math.fmod(p / 0.8 * lines, 1.0)
                self.pos[1] = bottom - (n * 20 + min(20.0, (frac + frac) * 20.0))
                n2 = int(p2 / 0.8 * lines)
                frac2 = math.fmod(p2 / 0.8 * lines, 1.0)
                if n != n2 or (p == 0.0 and p2 > 0.0):
                    self.events.append("sound " + ("printer-tear" if n2 == lines else "printer-feed"))
                if n == n2 and frac < 0.5 <= frac2:
                    self.events.append("sound printer-line")
            else:
                q = lerp_scale(p, 0.8, 1.0, 0.0, 1.0)
                end_y = bottom - (h + 20.0)
                self.pos[1] = (end_y - start_y) * (1.0 - (1.0 - q) ** 5) + start_y
                self.shadow = q < 0.5
                q2 = lerp_scale(p2, 0.8, 1.0, 0.0, 1.0)
                if q < 0.5 <= q2:
                    self.events.append("sound dragStop")
            self.anim = max(self.anim - dt, 0.0)
            self._end_reveal_if_done()
        elif kind == "SPITFROMRIGHT":
            t = max(0.0, min(1.0, 1.0 - (self.anim + self.anim)))
            start = desk[0] + desk[2]
            target = start - self.inner[0] - 20.0
            self.pos[0] = (target - start) * (1.0 - (1.0 - t) ** 4) + start
            old = self.anim
            self.anim = max(old - dt, 0.0)
            if 0.5 <= old and self.anim < 0.5:
                self.events.append("sound paper-spit")
            if self.anim == 0.0:
                self.state = NORMAL
                self.shadow = False
            else:
                self.shadow = True
        elif kind == "PRINTTOP":
            p = max(0.0, 1.0 - self.anim / PRINT_COUNTDOWN)
            p2 = max(0.0, 1.0 - (self.anim - dt) / PRINT_COUNTDOWN)
            top = desk[1]
            mid_y = top - 40.0
            if p < 0.8:
                start = top - self.inner[1]
                self.pos[1] = (p / 0.8) * (mid_y - start) + start
            else:
                q = lerp_scale(p, 0.8, 1.0, 0.0, 1.0)
                self.pos[1] = ((top + 20.0) - mid_y) * (1.0 - (1.0 - q) ** 5) + mid_y
                self.shadow = q < 0.5
                q2 = lerp_scale(p2, 0.8, 1.0, 0.0, 1.0)
                if q < 0.5 <= q2:
                    self.events.append("sound dragStop")
            self.anim = max(self.anim - dt, 0.0)
            self._end_reveal_if_done()
        else:
            self.state = NORMAL
        self.pos = [float(math_round(self.pos[0])), float(math_round(self.pos[1]))]

    def _end_reveal_if_done(self):
        if self.anim == 0.0:
            self.state = NORMAL
            self.shadow = False

    # -- hiding

    def start_hide(self, override=None):
        self.state = HIDING
        self.drop_vel = 0.0
        self.anim = HIDE_COUNTDOWN
        self.events.append("sound dragStart")
        if override:
            self.hide = override

    def animate_hide(self, dt):
        done = False
        if self.hide == "OFFBOTTOM":
            self.drop_vel += dt * 12000.0
            if self.placement == OUTER:
                self.pos[0] -= self.drop_vel * dt
                done = not (-self.outer[0] < self.pos[0])
            else:
                self.pos[1] += self.drop_vel * dt
                d = L["desk"]
                done = not (self.pos[1] < d[1] + d[3])
        else:  # TOFILER
            sx, sy = self.filer.slot_pos(self)
            tx, ty = L["filer"][0] + sx, self.filer.pos_y(1.0 if self.filer.open else 0.0) + sy
            if abs(self.pos[0] - tx) > 0.5:
                self.pos[0] += (tx - self.pos[0]) * 0.2
            elif abs(self.pos[1] - ty) > 0.5:
                self.pos[0] = tx
                self.pos[1] += (ty - self.pos[1]) * 0.2
            else:
                done = True
                self.pos = [tx, ty]
            self.set_placement(OUTER if inside(L["boothOuter"], self.pos[0], self.pos[1]) else FILER)
        if done:
            self.state = HIDDEN
            self.events.append("whenHidden")

    # -- dragging

    def start_drag(self, mouse):
        """startCustomDrag; mouse in booth coordinates."""
        if self.state != NORMAL or self.dragging:
            return False
        self.drag_start_placement = self.placement
        self.dragging = True
        self.moved = False
        self.was_dragged = True
        if self.placement == OUTER and self.dock:
            home = self.dock["home"]
            self.pos = [home[0], home[1] - 6.0]   # TOP entry: lifted 6 pixels
        self.drag_offset = [mouse[0] - self.pos[0], mouse[1] - self.pos[1]]
        self.drag_start = list(mouse)
        self.drag_cur = list(mouse)
        self.touch.start(mouse)
        self.events.append("moveDepthToTop")
        return True

    def drag_to(self, mouse):
        """The frame's part of updateCustomDrag, with the cursor at mouse."""
        self.drag_cur = list(mouse)
        mx, my = mouse
        self.touch.update(mouse)
        over_filer = self.filer_type != "NONE" and self.filer is not None and self._over_filer(mouse)
        started = self.drag_start_placement
        keep = lambda p: started == p
        if over_filer:
            self.set_placement(FILER)
            if keep(FILER) or (self.filer_type == "ONLYFILER" and started == INNER):
                self.pos = [mx - self.drag_offset[0], my - self.drag_offset[1]]
            else:
                fw, fh = self.filer_size
                self.pos = [mx - fw * 0.5, my - fh * 0.5]
            if not self.filer.open:
                self.filer.open = True
                self.events.append("filer open")
        elif inside(L["boothInner"], mx, my):
            self.set_placement(INNER)
            if keep(INNER) or (self.filer_type == "ONLYFILER" and started == FILER):
                self.pos = [mx - self.drag_offset[0], my - self.drag_offset[1]]
            else:
                self.pos = [mx - self.inner[0] * 0.5, my - self.inner[1] * 0.5]
            self.clamp()
            self.give_icon = False
        else:
            g = self.giveable(self)
            if self.mount and g != GIVE_YES_NOW and my <= L["boothMountDragBottomY"]:
                self.set_placement(MOUNT)
                if keep(MOUNT):
                    self.pos = [mx - self.drag_offset[0], my - self.drag_offset[1]]
                else:
                    self.pos = [mx - self.mount[0] * 0.5, my - self.mount[1] * 0.5]
                self.clamp()
            else:
                if keep(OUTER):
                    self.pos = [mx - self.drag_offset[0], my - self.drag_offset[1]]
                else:
                    self.pos = [mx - self.outer[0] * 0.5, my - self.outer[1] * 0.5]
                self.set_placement(OUTER)
                if self.dock:
                    hw, hh = self.outer[0] * 0.5, self.outer[1] * 0.5
                    cx, cy = dock_clamp_drag(self.dock, (self.pos[0] + hw, self.pos[1] + hh),
                                             self.outer[0], self.outer[1])
                    self.pos = [cx - hw, cy - hh]
                else:
                    self.clamp()
                give = L["give"]
                bottom = self.outer[1] + self.pos[1]
                self.give_icon = (g == GIVE_YES_NOW and give[0] <= mx < give[0] + give[2]
                                  and give[1] <= bottom < give[1] + give[3])
        self.pos = [float(math_round(self.pos[0])), float(math_round(self.pos[1]))]
        if not self.moved and cheb_floor(self.drag_cur, self.drag_start) > 1.0:
            self.events.append("sound dragStart")
            self.moved = True
        self.shadow = self.placement == INNER and self.moved
        self.events.append("moveDepthToTop")

    def _over_filer(self, mouse):
        """isOverFiler: right of the desk's left edge, below the drawer's top
        and left of the drawer's right edge; no lower or other left limit.
        (The drawer's top while it slides is between the open and closed
        values; only the end values are modelled here.)"""
        drawer_top = self.filer.pos_y(1.0 if self.filer.open else 0.0)
        drawer_right = L["filer"][0] + self.filer.back_w
        return L["desk"][0] < mouse[0] and drawer_top < mouse[1] and mouse[0] < drawer_right

    def end_drag(self):
        """endCustomDrag. Returns the list of things that happen."""
        out = []
        self.dragging = False
        if self.moved:
            out.append("sound dragStop")
        self.moved = False
        self.touch.stop()
        self.shadow = False
        if self.placement == FILER:
            out.append("commitToFiler")
            self.put_in_filer_once = True
        elif self.placement == MOUNT:
            self.pos[1] += MOUNT_DROP_SINK
        out.append("moveDepthToTop")
        if self.drag_start_placement == FILER and self.placement != FILER:
            out.append("whenRemoveFromFiler first=%s" % (not self.removed_from_filer_once))
            self.removed_from_filer_once = True
        if self.mount:
            out.append("whenMounted %s" % (self.placement == MOUNT))
        if self.give_icon and self.giveable(self) == GIVE_YES_NOW:
            self.state = GIVING
            out.append("GIVING")
        self.give_icon = False
        self.drop_vel = 0.0
        if cheb_floor(self.drag_cur, self.drag_start) < DRAG_CLICK_DIST:
            out.append("click at %s" % (self.drag_cur,))
        self.events += out
        return out

    # -- every frame

    def update(self, dt):
        """DeskItem.update (the drag's own part comes from drag_to)."""
        if self.state == HIDING:
            self.animate_hide(dt)
        elif self.state in (HIDDEN, GIVEN):
            pass
        elif self.state == REVEALING:
            self.animate_reveal(dt)
        elif self.state == GIVING:
            if L["counterTopEdgeY"] < self.pos[1]:
                self.visible = False
                self.state = GIVEN
                self.events += ["sound givetake-close", "whenGiven"]
                return
            self.drop_vel = self.drop_vel + 3000.0 * dt if self.drop_vel >= 1.0 else 1.0
            self.pos[1] += self.drop_vel * dt
        elif self.state == RETURNINGTODOCK:
            if self.placement != OUTER:
                # OUTER_LEFT: slide left at 750 px/s until half past the desk's edge
                self.pos[0] -= dt * 750.0
                edge = L["boothInner"][0]
                if self.pos[0] < edge - self.inner[0] * 0.5:
                    self.pos[0] = float(int(math.floor(edge - self.outer[0] * 0.5)))
                    self.pos[1] = int(math.floor(self.inner[1] * 0.5)) + self.pos[1]
                    self.set_placement(OUTER)
                self.pos = [float(int(math.floor(self.pos[0]))), float(int(math.floor(self.pos[1])))]
            else:
                self.state = NORMAL
        elif not self.dragging:
            if self.placement == OUTER:
                accel = dt * 3000.0
                if self.dock:
                    x, y, landed, self.drop_vel = dock_return_home(
                        self.dock, self.pos[0], self.pos[1], dt, self.drop_vel, accel)
                    self.pos = [x, y]
                    if landed:
                        self.events += ["sound drop", "sound dragStop"]
                    return
                floor_y = L["outerFloorMidY"] - self.outer[1] * 0.5
                if self.pos[1] < floor_y:
                    self.touch.apply_decay(self.pos, dt)
                    self.clamp()
                    self.drop_vel += accel
                    self.pos[1] += max(1.0, self.drop_vel * dt)
                    if floor_y < self.pos[1]:
                        self.pos[1] = floor_y
                        self.events += ["sound drop", "sound dragStop"]
                        self.touch.vel = [0.0, 0.0]
                else:
                    self.drop_vel = 0.0
                    self.pos[1] = floor_y
            elif self.placement == FILER:
                sx, sy = self.filer.slot_pos(self)
                px, py = self.pos_in_filer
                if (py - sy) ** 2 + (px - sx) ** 2 < 1.0:
                    self.pos_in_filer = [sx, sy]
                else:
                    self.pos_in_filer = [(sx - px) * 0.5 + px, (sy - py) * 0.5 + py]
                self.pos = [L["filer"][0] + self.pos_in_filer[0],
                            self.filer.pos_y(1.0 if self.filer.open else 0.0) + self.pos_in_filer[1]]
            elif self.placement == INNER and self.touch.has_vel():
                self.touch.apply_decay(self.pos, dt)
                self.clamp()


# ------------------------------------------------------------- demo

def run(item, frames, dt=1.0 / 60.0, every=1):
    rows = []
    for f in range(frames):
        item.update(dt)
        if f % every == 0 or item.state == NORMAL:
            rows.append((f + 1, item.state, tuple(item.pos)))
        if item.state in (NORMAL, HIDDEN, GIVEN):
            break
    return rows


def main(argv):
    print("a passport (closed 30 x 42) from the slot:")
    p = DeskItem((30, 42), (60, 80))
    p.start_reveal()
    print("  start", p.pos)
    for row in run(p, 120, every=3):
        print("  ", row)
    print("a citation (page 100 x 120) printed from the bottom:")
    c = DeskItem((50, 26), (100, 120), reveal=("PRINTBOTTOM",))
    c.start_reveal()
    for row in run(c, 400, every=30):
        print("  ", row)
    print("  sounds:", [e for e in c.events if e.startswith("sound")])


if __name__ == "__main__":
    main(sys.argv)
