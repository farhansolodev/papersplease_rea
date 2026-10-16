"""Input handling: app.ent.Input and app.ent.Pointer, as the desktop game
runs them (docs/input-handling.md).

- host_to_game: the mouse position on the game's quad to game pixels;
- Pointer: one pointer's frame update (down, just down, just up, the
  positions, the double click, being taken by an entity, the cursor);
- Input: the keys with "masked until release", the masked areas,
  getPointerOver, getPointerJustDown, hiding the pointers for a frame;
- frame_order: what one frame does, in order.
Pure Python.
"""

import math

POINTER_COUNT = 3          # Input.POINTER_COUNT
DOUBLE_CLICK_SPAN = 0.2    # seconds (Pointer.willDoubleClick; Input.kDoubleClickSpan)
DOUBLE_CLICK_DIST = 2.0    # pixels, straight-line
DRAG_CLICK_DIST = 4.0      # Input.kDragClickDist (DeskItem uses its own 4)
SCREEN = (0.0, 0.0, 570.0, 320.0)   # the input's limit rectangle on desktop


def host_to_game(qx, qy, width=570, height=320):
    """HostUnity.Update: a point on the screen quad (its own coordinates,
    -0.5..0.5 each way) to game pixels: x = floor((qx + 0.5) x width),
    y = floor(height - (qy + 0.5) x height) (y grows downward in the game)."""
    return float(math.floor((qx + 0.5) * width)), float(math.floor(height - (qy + 0.5) * height))


def inside(r, x, y):
    return r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]


class Pointer:
    def __init__(self, pid):
        self.id = pid
        self.down = self.just_down = self.just_up = False
        self.world = (0.0, 0.0)
        self.pre_world = (0.0, 0.0)
        self.unclamped = (0.0, 0.0)
        self.cursor = None
        self.capturing = None
        self.capture_countdown = 0
        self.just_double = False
        self.just_down_time = -1000.0
        self.just_down_world = (0.0, 0.0)
        self.mask_until_release = False
        self.from_touch = False

    def update(self, host_down, host_pos, now, from_touch=False, limit=SCREEN):
        """Pointer.update, one frame."""
        down = host_down
        if self.mask_until_release:
            if not host_down:
                self.mask_until_release = False
            down = False
        self.from_touch = from_touch
        self.just_down = (not self.down) and down
        self.just_up = self.down and not down
        self.down = down
        self.pre_world = self.world
        x = min(max(host_pos[0], limit[0]), limit[0] + limit[2])
        y = min(max(host_pos[1], limit[1]), limit[1] + limit[3])
        self.world = (x, y)
        self.unclamped = host_pos
        self.cursor = None
        if self.capture_countdown < 1:
            self.capturing = None
        else:
            self.capture_countdown = max(0, self.capture_countdown - 1)
            if self.capture_countdown < 1:
                self.capturing = None
        if self.just_down:
            self.just_double = self.will_double_click(self.world, now)
            self.just_down_time = now
            self.just_down_world = self.world
        else:
            self.just_double = False

    def will_double_click(self, pos, now):
        if DOUBLE_CLICK_SPAN <= now - self.just_down_time:
            return False
        d = math.hypot(self.just_down_world[0] - pos[0], self.just_down_world[1] - pos[1])
        return d < DOUBLE_CLICK_DIST

    def capture(self, ent):
        """captureUntilNextFrameEnd: the entity keeps the pointer for the
        rest of this frame and all of the next one."""
        self.capturing = ent
        self.capture_countdown = 2

    def set_cursor(self, cursor):
        """The first entity to ask this frame wins."""
        if self.cursor is None:
            self.cursor = cursor

    def active(self):
        return (not self.from_touch) or self.down or self.just_up


class Input:
    def __init__(self, n_keys=11):
        self.pointers = [Pointer(i) for i in range(POINTER_COUNT)]
        self.cur_keys = [False] * n_keys
        self.pre_keys = [False] * n_keys
        self.key_mask = [False] * n_keys
        self.masked_areas = []
        self.hide_countdown = 0
        self.host_want_visible_cursor = True

    def update(self, host_keys, host_pointers, now, want_visible_cursor=True):
        """Input.update: keys, pointers, then the masked areas are cleared."""
        self.host_want_visible_cursor = want_visible_cursor
        for k, host_down in enumerate(host_keys):
            self.pre_keys[k] = self.cur_keys[k]
            if host_down:
                self.cur_keys[k] = not self.key_mask[k]
            else:
                self.cur_keys[k] = False
                self.key_mask[k] = False
        for p, (down, pos, touch) in zip(self.pointers, host_pointers):
            p.update(down, pos, now, touch)
        self.masked_areas = []
        if self.hide_countdown > 0:
            self.hide_countdown -= 1

    # -- keys
    def key_down(self, k):
        return self.cur_keys[k]

    def key_just_down(self, k):
        return self.cur_keys[k] and not self.pre_keys[k]

    def key_just_up(self, k):
        return (not self.cur_keys[k]) and self.pre_keys[k]

    def mask_key_until_release(self, k):
        self.cur_keys[k] = False
        self.key_mask[k] = True

    # -- areas
    def mask_area(self, rect):
        """maskAreaUntilFrameEnd: no later asker this frame sees a pointer here."""
        self.masked_areas.append(rect)

    def in_masked_area(self, pos):
        return any(inside(r, pos[0], pos[1]) for r in self.masked_areas)

    # -- pointers
    def pointer_over(self, ent, rect, only_id=-1):
        """getPointerOver: first a pointer this entity has taken (anywhere,
        unless masked); else the first free pointer inside the rectangle and
        not masked, preferring one that is held."""
        for p in self.pointers:
            if only_id >= 0 and p.id != only_id:
                continue
            if p.active() and p.capturing is ent and not self.in_masked_area(p.world):
                return p
        found = None
        for p in self.pointers:
            if only_id >= 0 and p.id != only_id:
                continue
            if not p.active() or p.capturing is not None:
                continue
            if inside(rect, p.world[0], p.world[1]) and not self.in_masked_area(p.world):
                if p.down:
                    return p
                if found is None:
                    found = p
        return found

    def pointer_just_down(self, ent, rect, cursor="HAND"):
        """getPointerJustDown (checkPointerJustDown): a pointer over the
        rectangle masks it for the frame and sets the cursor; if it was
        pressed this frame the entity takes it and it is returned."""
        p = self.pointer_over(ent, rect)
        if p is None or not inside(rect, p.world[0], p.world[1]):
            return None
        self.mask_area(rect)
        if cursor:
            p.set_cursor(cursor)
        if p.just_down:
            p.capture(ent)
            return p
        return None

    def mask_all_pointers_until_release(self):
        for p in self.pointers:
            p.mask_until_release = True

    def hide_pointers_for_one_frame(self):
        self.hide_countdown = 1

    def want_visible_cursor(self):
        return self.host_want_visible_cursor and self.hide_countdown == 0


CURSOR_PICTURES = {"ARROW": "assets/CursorArrow.png", "HAND": "assets/CursorHand.png"}
CURSOR_LAYER = 100


def cursor_sprite_pos(cursor, pointer_unclamped, custom_size=None):
    """CursorEnt.react: where the cursor picture's top left goes. Arrow
    (and no cursor) -1, -1; hand -6, -2; a custom picture centred,
    floor(-w/2), floor(-h/2) (the rifle scopes, 47 x 47: -24, -24)."""
    if cursor == "HAND":
        off = (-6.0, -2.0)
    elif cursor == "CUSTOM":
        off = (float(math.floor(-custom_size[0] * 0.5)), float(math.floor(-custom_size[1] * 0.5)))
    else:
        off = (-1.0, -1.0)
    return pointer_unclamped[0] + off[0], pointer_unclamped[1] + off[1]


def frame_order():
    """One frame of the desktop game (HostUnity.Update, Game.update, Game.draw)."""
    return [
        "host: hide the system cursor; read the 11 keys and the 3 pointers",
        "Input.update: keys (with masks), each Pointer.update, clear masked areas",
        "Game.update: Escape pauses if the screen allows (key masked until release)",
        "game clock, then the game's own state machine",
        "entity tree: update (first child to last, parents before children)",
        "music, then all-time statistics (which may show an achievement popup)",
        "entity tree: react (last child to first, children before their parent)",
        "speaker (sounds), settings applied if changed, screenshot key (O)",
        "Game.draw: the entity tree drawn (first child to last)",
    ]


if __name__ == "__main__":
    for line in frame_order():
        print("-", line)
    print(host_to_game(0.0, 0.0), host_to_game(-0.5, 0.5), host_to_game(0.4999, -0.4999))
