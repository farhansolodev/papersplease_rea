//! Input as the desktop game sees it: `app.ent.Input` and `app.ent.Pointer`
//! (docs/input-handling.md), the same as scripts/reference/inputs.py for
//! pointer 0, the mouse. Pointers 1 and 2 are touch pointers that are never
//! down on desktop, so every question about pointers passes over them; they
//! are left out.

use crate::raster::Quad;

/// The game's 11 keys (`app.ent.Key`, docs/screens.md part 4).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Key {
    Tab = 0,
    Space = 1,
    Enter = 2,
    Left = 3,
    Right = 4,
    Escape = 5,
    T = 6,
    DevMenu = 7,
    AutoplayAbort = 8,
    AutoplayPause = 9,
    Screenshot = 10,
}

pub const KEY_COUNT: usize = 11;

/// Pointer.willDoubleClick: under 0.2 s and under 2 pixels.
const DOUBLE_CLICK_SPAN: f64 = 0.2;
const DOUBLE_CLICK_DIST: f64 = 2.0;

/// Who asks about the pointer: a number the screen gives each of its parts.
pub type EntId = u32;

/// `app.ent.Cursor` (the custom kind, the rifles' scopes, comes later).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Cursor {
    Arrow,
    Hand,
}

/// What the host read this frame.
#[derive(Debug, Clone, Copy, Default)]
pub struct HostInput {
    /// Each game key held.
    pub keys: [bool; KEY_COUNT],
    /// The mouse has moved or been pressed since the start (the original's
    /// input mode 1). Before that pointer 0 is invalid.
    pub mouse_valid: bool,
    /// The mouse in whole game pixels, not held inside the screen.
    pub mouse: (f64, f64),
    /// The left button held.
    pub left_down: bool,
}

/// A rectangle (x, y, width, height): left and top edges in, right and
/// bottom out.
pub type Rect = [f64; 4];

fn inside(r: &Rect, x: f64, y: f64) -> bool {
    r[0] <= x && x < r[0] + r[2] && r[1] <= y && y < r[1] + r[3]
}

/// Pointer 0.
#[derive(Debug, Clone)]
pub struct Pointer {
    /// From the mouse (else a "touch" pointer that is never down).
    pub from_mouse: bool,
    pub down: bool,
    pub just_down: bool,
    pub just_up: bool,
    /// Held inside the screen, 0..570 and 0..320 with both ends.
    pub pos: (f64, f64),
    pub pre_pos: (f64, f64),
    /// As given (the drawn cursor uses this one).
    pub unclamped: (f64, f64),
    /// The first part to set it this frame wins.
    pub cursor: Option<Cursor>,
    capturing: Option<EntId>,
    capture_countdown: u32,
    pub just_double: bool,
    just_down_time: f64,
    just_down_pos: (f64, f64),
    mask_until_release: bool,
}

impl Pointer {
    fn new() -> Pointer {
        Pointer {
            from_mouse: false,
            down: false,
            just_down: false,
            just_up: false,
            pos: (0.0, 0.0),
            pre_pos: (0.0, 0.0),
            unclamped: (0.0, 0.0),
            cursor: None,
            capturing: None,
            capture_countdown: 0,
            just_double: false,
            just_down_time: -1000.0,
            just_down_pos: (0.0, 0.0),
            mask_until_release: false,
        }
    }

    fn update(&mut self, host_down: bool, host_pos: (f64, f64), from_mouse: bool, now: f64) {
        let mut down = host_down;
        if self.mask_until_release {
            if !host_down {
                self.mask_until_release = false;
            }
            down = false;
        }
        self.from_mouse = from_mouse;
        self.just_down = !self.down && down;
        self.just_up = self.down && !down;
        self.down = down;
        self.pre_pos = self.pos;
        let (w, h) = (crate::screen::WIDTH as f64, crate::screen::HEIGHT as f64);
        self.pos = (host_pos.0.clamp(0.0, w), host_pos.1.clamp(0.0, h));
        self.unclamped = host_pos;
        self.cursor = None;
        if self.capture_countdown > 0 {
            self.capture_countdown -= 1;
        }
        if self.capture_countdown < 1 {
            self.capturing = None;
        }
        if self.just_down {
            let (dx, dy) = (self.just_down_pos.0 - self.pos.0, self.just_down_pos.1 - self.pos.1);
            self.just_double = now - self.just_down_time < DOUBLE_CLICK_SPAN && dx.hypot(dy) < DOUBLE_CLICK_DIST;
            self.just_down_time = now;
            self.just_down_pos = self.pos;
        } else {
            self.just_double = false;
        }
    }

    /// `captureUntilNextFrameEnd`: the part keeps the pointer for the rest of
    /// this frame and all of the next one.
    pub fn capture(&mut self, ent: EntId) {
        self.capturing = Some(ent);
        self.capture_countdown = 2;
    }

    pub fn is_capturing(&self, ent: EntId) -> bool {
        self.capturing == Some(ent)
    }

    pub fn set_cursor(&mut self, cursor: Cursor) {
        if self.cursor.is_none() {
            self.cursor = Some(cursor);
        }
    }

    /// A touch pointer that is neither down nor just let go is passed over.
    fn active(&self) -> bool {
        self.from_mouse || self.down || self.just_up
    }
}

/// `app.ent.Input`.
pub struct Input {
    pub pointer: Pointer,
    cur_keys: [bool; KEY_COUNT],
    pre_keys: [bool; KEY_COUNT],
    key_mask: [bool; KEY_COUNT],
    masked_areas: Vec<Rect>,
    hide_countdown: u32,
    want_visible_cursor: bool,
    /// The input's own clock, for the double click.
    time: f64,
}

impl Default for Input {
    fn default() -> Self {
        Self::new()
    }
}

impl Input {
    pub fn new() -> Input {
        Input {
            pointer: Pointer::new(),
            cur_keys: [false; KEY_COUNT],
            pre_keys: [false; KEY_COUNT],
            key_mask: [false; KEY_COUNT],
            masked_areas: Vec::new(),
            hide_countdown: 0,
            want_visible_cursor: false,
            time: 0.0,
        }
    }

    /// `Input.update`, at the start of a frame of `dt` seconds.
    pub fn update(&mut self, host: &HostInput, dt: f64) {
        self.time += dt;
        for k in 0..KEY_COUNT {
            self.pre_keys[k] = self.cur_keys[k];
            if host.keys[k] {
                self.cur_keys[k] = !self.key_mask[k];
            } else {
                self.cur_keys[k] = false;
                self.key_mask[k] = false;
            }
        }
        // An invalid pointer keeps its old position and is not down.
        let pos = if host.mouse_valid { host.mouse } else { self.pointer.unclamped };
        self.pointer.update(host.mouse_valid && host.left_down, pos, host.mouse_valid, self.time);
        self.want_visible_cursor = host.mouse_valid;
        self.masked_areas.clear();
        if self.hide_countdown > 0 {
            self.hide_countdown -= 1;
        }
    }

    pub fn key_down(&self, k: Key) -> bool {
        self.cur_keys[k as usize]
    }

    pub fn key_just_down(&self, k: Key) -> bool {
        self.cur_keys[k as usize] && !self.pre_keys[k as usize]
    }

    pub fn key_just_up(&self, k: Key) -> bool {
        !self.cur_keys[k as usize] && self.pre_keys[k as usize]
    }

    pub fn any_key_just_down(&self) -> bool {
        (0..KEY_COUNT).any(|k| self.cur_keys[k] && !self.pre_keys[k])
    }

    pub fn mask_key_until_release(&mut self, k: Key) {
        self.cur_keys[k as usize] = false;
        self.key_mask[k as usize] = true;
    }

    /// `maskAreaUntilFrameEnd`: no part asked later this frame sees a
    /// pointer there.
    pub fn mask_area(&mut self, rect: Rect) {
        self.masked_areas.push(rect);
    }

    fn in_masked_area(&self, (x, y): (f64, f64)) -> bool {
        self.masked_areas.iter().any(|r| inside(r, x, y))
    }

    /// `getIntersectsMaskedArea`: does the rectangle touch a blocked area
    /// (here all edges count).
    pub fn intersects_masked_area(&self, r: &Rect) -> bool {
        self.masked_areas
            .iter()
            .any(|m| r[0] <= m[0] + m[2] && m[0] <= r[0] + r[2] && r[1] <= m[1] + m[3] && m[1] <= r[1] + r[3])
    }

    /// `getPointerOver`: the pointer if this part has taken it (anywhere,
    /// unless blocked), or if no part has and it is inside the rectangle and
    /// not blocked.
    pub fn pointer_over(&mut self, ent: EntId, rect: &Rect) -> Option<&mut Pointer> {
        let p = &self.pointer;
        if !p.active() || self.in_masked_area(p.pos) {
            return None;
        }
        let ok = p.is_capturing(ent) || (p.capturing.is_none() && inside(rect, p.pos.0, p.pos.1));
        if ok { Some(&mut self.pointer) } else { None }
    }

    /// `getPointerJustDown`: a pointer over the rectangle blocks it for the
    /// frame and sets the cursor (the hand if none is given); if it was
    /// pressed this frame the part takes it and the answer is yes.
    pub fn pointer_just_down(&mut self, ent: EntId, rect: &Rect, cursor: Option<Cursor>) -> bool {
        let Some(p) = self.pointer_over(ent, rect) else { return false };
        if !inside(rect, p.pos.0, p.pos.1) {
            return false;
        }
        p.set_cursor(cursor.unwrap_or(Cursor::Hand));
        let just_down = p.just_down;
        if just_down {
            p.capture(ent);
        }
        self.mask_area(*rect);
        just_down
    }

    pub fn mask_all_pointers_until_release(&mut self) {
        self.pointer.mask_until_release = true;
    }

    pub fn hide_pointers_for_one_frame(&mut self) {
        self.hide_countdown = 1;
    }

    pub fn want_visible_cursor(&self) -> bool {
        self.want_visible_cursor && self.hide_countdown == 0
    }
}

/// The game's own cursor (`play.ui.CursorEnt`), drawn above everything:
/// the arrow (or no cursor set) with its top left at (-1, -1) from the
/// pointer, the hand at (-6, -2). Placed at the pointer as given, so it can
/// run off the screen. `pictures` are the arrow's and the hand's.
pub fn cursor_quad(input: &Input, arrow: (usize, u32, u32), hand: (usize, u32, u32)) -> Option<Quad> {
    if !input.want_visible_cursor() {
        return None;
    }
    let p = &input.pointer;
    let ((image, w, h), (dx, dy)) = match p.cursor {
        Some(Cursor::Hand) => (hand, (-6.0, -2.0)),
        _ => (arrow, (-1.0, -1.0)),
    };
    let (x, y) = (p.unclamped.0 + dx, p.unclamped.1 + dy);
    Some(Quad { image, x0: x, y0: y, x1: x + w as f64, y1: y + h as f64, src: [0, 0, w as i32, h as i32], color: 0xFFFF_FFFF })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn frame(input: &mut Input, x: f64, y: f64, down: bool) {
        let host = HostInput { keys: [false; KEY_COUNT], mouse_valid: true, mouse: (x, y), left_down: down };
        input.update(&host, 1.0 / 60.0);
    }

    #[test]
    fn no_pointer_before_the_mouse_first_moves() {
        let mut input = Input::new();
        input.update(&HostInput::default(), 1.0 / 60.0);
        assert!(input.pointer_over(1, &[0.0, 0.0, 570.0, 320.0]).is_none());
        assert!(!input.want_visible_cursor());
        frame(&mut input, 5.0, 5.0, false);
        assert!(input.pointer_over(1, &[0.0, 0.0, 570.0, 320.0]).is_some());
    }

    #[test]
    fn a_take_lasts_to_the_end_of_the_next_frame() {
        let mut input = Input::new();
        frame(&mut input, 5.0, 5.0, true);
        input.pointer.capture(7);
        assert!(input.pointer_over(8, &[0.0, 0.0, 10.0, 10.0]).is_none());
        frame(&mut input, 50.0, 50.0, true);
        assert!(input.pointer_over(7, &[0.0, 0.0, 10.0, 10.0]).is_some(), "taken: found anywhere");
        frame(&mut input, 5.0, 5.0, true);
        assert!(input.pointer_over(8, &[0.0, 0.0, 10.0, 10.0]).is_some(), "free again");
    }

    #[test]
    fn a_blocked_area_hides_the_pointer_from_later_parts() {
        let mut input = Input::new();
        frame(&mut input, 5.0, 5.0, true);
        assert!(input.pointer_just_down(1, &[0.0, 0.0, 10.0, 10.0], None));
        assert_eq!(input.pointer.cursor, Some(Cursor::Hand));
        assert!(input.pointer_over(2, &[0.0, 0.0, 570.0, 320.0]).is_none());
    }

    #[test]
    fn positions_are_held_inside_the_screen_but_the_cursor_is_not() {
        let mut input = Input::new();
        frame(&mut input, -3.0, 400.0, false);
        assert_eq!(input.pointer.pos, (0.0, 320.0));
        let q = cursor_quad(&input, (1, 19, 26), (2, 19, 26)).unwrap();
        assert_eq!((q.image, q.x0, q.y0), (1, -4.0, 399.0));
    }

    #[test]
    fn a_double_click_is_under_0_2_s_and_2_pixels() {
        let mut input = Input::new();
        frame(&mut input, 5.0, 5.0, true);
        frame(&mut input, 5.0, 5.0, false);
        frame(&mut input, 6.0, 6.0, true);
        assert!(input.pointer.just_double, "1.41 pixels, 2 frames");
        frame(&mut input, 6.0, 6.0, false);
        frame(&mut input, 9.0, 6.0, true);
        assert!(!input.pointer.just_double, "3 pixels");
    }

    #[test]
    fn masked_keys_and_pointers_wait_for_release() {
        let mut input = Input::new();
        let mut host = HostInput { mouse_valid: true, left_down: true, ..HostInput::default() };
        host.keys[Key::Escape as usize] = true;
        input.update(&host, 0.0);
        assert!(input.key_just_down(Key::Escape) && input.any_key_just_down());
        input.mask_key_until_release(Key::Escape);
        input.mask_all_pointers_until_release();
        input.update(&host, 0.0);
        assert!(!input.key_down(Key::Escape) && !input.pointer.down);
        host.keys[Key::Escape as usize] = false;
        host.left_down = false;
        input.update(&host, 0.0);
        host.keys[Key::Escape as usize] = true;
        host.left_down = true;
        input.update(&host, 0.0);
        assert!(input.key_just_down(Key::Escape) && input.pointer.just_down);
    }
}
