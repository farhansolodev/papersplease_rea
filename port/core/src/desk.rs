//! A paper on the desk (`play.day.booth.DeskItem` made by a `Paper`), as
//! far as milestone 4c needs it for the rulebook: closed on the counter
//! side at its dock, or open on the desk; dragged, thrown, going back to
//! its dock; its sounds, its cursor, its pictures cut to their clip
//! rectangles. docs/desk-movement.md, docs/desk-pictures.md and
//! docs/milestone-4.md ("4c"); scripts/reference/rulebook.py (on
//! deskmove.py and deskpics.py) does the same frame by frame.
//!
//! Not here yet: the other reveals and the hide animations, the drawer,
//! the wall, giving, following a link on a click (4d), the double click.
//! All positions are in booth coordinates (the booth is at y 103).

use crate::aud::{AudioHost, Speaker};
use crate::input::{Cursor, EntId, Input, Rect};
use crate::pages::{Builder, Gallery};
use crate::raster::Quad;
use crate::paper::{Placed, SoundSet, Visual};

const BOOTH_Y: f64 = 103.0;
/// `Layout` values (docs/booth-layout.md).
const BOOTH_INNER_X: f64 = 178.0; // boothInner: x 178 and right, any y
const BOOTH_INNER_CLIP: [f64; 4] = [180.0, 0.0, 5390.0, 217.0];
const BOOTH_INNER_CLAMP: [f64; 4] = [178.0, 0.0, 392.0, 217.0];
const BOOTH_OUTER: [f64; 4] = [0.0, 0.0, 178.0, 217.0];
/// `DeskItem`'s statics.
const DRAG_CLICK_DIST: i64 = 4;
const SHADOW_OFFSET: (f64, f64) = (4.0, 4.0);
const SHADOW_ALPHA: f64 = 0.5;
/// `app.Clock.maxDeltaTime`.
const MAX_DT: f64 = 0.1;
/// TouchDrag's decay per 1/60 s.
const DECAY: f64 = 0.75;

/// A dock point (entry `TOP`): the paper's home and its drag clamp.
#[derive(Debug, Clone, Copy)]
pub struct Dock {
    pub home: [f64; 4],
    pub clamp: [f64; 4],
}

/// The rulebook's dock (`Layout.dockPoints`, key `rules`).
pub const RULES_DOCK: Dock = Dock { home: [113.0, 174.0, 26.0, 34.0], clamp: [0.0, 0.0, 570.0, 178.0] };

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Placement {
    Outer,
    Inner,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    Revealing,
    Normal,
}

/// Haxe's `Math.round` as compiled (deskmove.math_round).
fn math_round(x: f64) -> f64 {
    let i = x.trunc();
    let d = x - i;
    if d >= 1.0 || -1.0 >= d {
        i
    } else if d >= 0.5 {
        i + 1.0
    } else if -0.5 > d {
        i - 1.0
    } else {
        i
    }
}

fn lerp_scale(v: f64, in_min: f64, in_max: f64, out_min: f64, out_max: f64) -> f64 {
    let v = v.min(in_max).max(in_min);
    (v - in_min) / (in_max - in_min) * (out_max - out_min) + out_min
}

/// max(floor|dx|, floor|dy|): how far the drag has gone, in whole pixels.
fn cheb_floor(a: (f64, f64), b: (f64, f64)) -> i64 {
    ((a.0 - b.0).abs().floor() as i64).max((a.1 - b.1).abs().floor() as i64)
}

fn inside(r: &[f64; 4], x: f64, y: f64) -> bool {
    r[0] <= x && x < r[0] + r[2] && r[1] <= y && y < r[1] + r[3]
}

/// `DeskItem.clip`: the visual's rectangle (at `visual` in the item at
/// `item`, of `size`) cut to `bounds`, back in the item's coordinates.
fn clip_rect(item: (f64, f64), visual: (f64, f64), size: (f64, f64), bounds: &[f64; 4]) -> [f64; 4] {
    let (x, y) = (visual.0 + item.0, visual.1 + item.1);
    let left = x.max(bounds[0]);
    let right = left.max((size.0 + x).min(bounds[2] + bounds[0]));
    let top = y.max(bounds[1]);
    let bottom = top.max((size.1 + y).min(bounds[3] + bounds[1]));
    [left - item.0, top - item.1, right - left, bottom - top]
}

/// `Visual.hitRect`: (x, y, w, h) cut to the clip rectangle.
fn hit_rect(pos: (f64, f64), size: (f64, f64), clip: &[f64; 4]) -> [f64; 4] {
    let left = pos.0.max(clip[0]);
    let right = left.max((size.0 + pos.0).min(clip[2] + clip[0]));
    let top = pos.1.max(clip[1]);
    let bottom = top.max((size.1 + pos.1).min(clip[3] + clip[1]));
    [left, top, right - left, bottom - top]
}

/// `PaperInnerVisuals.compareProximity` (deskpics.compare_proximity):
/// negative when `ra` is the better pick for `p`, positive for `rb`.
fn compare_proximity(p: (f64, f64), ra: &[f64; 4], rb: &[f64; 4]) -> i32 {
    const SAME: f64 = 1.0;
    const WIDE: f64 = 15.0;
    const FACTOR: f64 = 0.75;
    const ROUNDS: usize = 5;
    if ra == rb {
        return 0;
    }
    let [ax, ay, aw, ah] = *ra;
    let [bx, by, bw, bh] = *rb;
    if bh <= ah && ay <= by && bh + by <= ah + ay && bw <= aw && ax <= bx && bx + bw <= ax + aw {
        return 1;
    }
    if ah <= bh && by <= ay && ah + ay <= bh + by && aw <= bw && bx <= ax && ax + aw <= bx + bw {
        return -1;
    }
    if (ah - bh).abs() < SAME && ((ax - bx).abs() < SAME || ((aw + ax) - (bw + bx)).abs() < SAME) {
        let da = (p.1 - (ah * 0.5 + ay).floor()).abs();
        let db = (p.1 - (bh * 0.5 + by).floor()).abs();
        if aw >= WIDE {
            if bw < WIDE && db * FACTOR < da {
                return 1;
            }
        } else if bw >= WIDE && da * FACTOR < db {
            return -1;
        }
    }
    let (mut a, mut b) = (*ra, *rb);
    for _ in 0..ROUNDS {
        for r in [&mut a, &mut b] {
            r[0] += 1.0;
            r[1] += 1.0;
            r[2] -= 2.0;
            r[3] -= 2.0;
        }
        let (in_a, in_b) = (inside(&a, p.0, p.1), inside(&b, p.0, p.1));
        if in_a && !in_b {
            return -1;
        }
        if in_b && !in_a {
            return 1;
        }
        if !(in_a || in_b) {
            break;
        }
    }
    let dist2 = |r: &[f64; 4]| {
        if inside(r, p.0, p.1) {
            return 0.0;
        }
        let cx = p.0.max(r[0]).min(r[0] + r[2]);
        let cy = p.1.max(r[1]).min(r[1] + r[3]);
        (p.0 - cx).powi(2) + (p.1 - cy).powi(2)
    };
    let (d_a, d_b) = (dist2(ra), dist2(rb));
    if d_a < d_b {
        return -1;
    }
    if d_b < d_a {
        return 1;
    }
    let middle = |r: &[f64; 4]| {
        let mx = (r[2] * 0.5 + r[0]).floor();
        let my = (r[3] * 0.5 + r[1]).floor();
        (p.0 - mx).abs().floor() + (p.1 - my).abs().floor()
    };
    let (m_a, m_b) = (middle(ra), middle(rb));
    if m_a < m_b {
        -1
    } else if m_b < m_a {
        1
    } else {
        0
    }
}

/// `app.Clock` counted in frames: `start` makes the next update give 0;
/// an update gives the frames since the one before times the step, at
/// most 0.1 s (real time passes on frames it is not updated in).
#[derive(Debug, Clone, Copy, Default)]
struct FrameClock {
    started: bool,
    last: u64,
    dt: f64,
}

impl FrameClock {
    fn start(&mut self) {
        self.started = false;
    }

    fn update(&mut self, tick: u64, step: f64) {
        if self.started {
            self.dt = ((tick - self.last) as f64 * step).min(MAX_DT);
        } else {
            self.started = true;
            self.dt = 0.0;
        }
        self.last = tick;
    }
}

/// `booth.TouchDrag`: the drag's speed (pixels a second) and the slide
/// after it, with its own clock.
#[derive(Debug, Clone, Copy, Default)]
struct TouchDrag {
    vel: (f64, f64),
    touching: bool,
    touch: (f64, f64),
    clock: FrameClock,
}

impl TouchDrag {
    fn start(&mut self, touch: (f64, f64)) {
        self.touch = touch;
        self.vel = (0.0, 0.0);
        self.clock.start();
        self.touching = true;
    }

    fn update(&mut self, touch: (f64, f64), tick: u64, step: f64) {
        self.clock.update(tick, step);
        let (dx, dy) = (touch.0 - self.touch.0, touch.1 - self.touch.1);
        self.touch = touch;
        self.vel.0 += (dx * 60.0 - self.vel.0) * 0.5;
        self.vel.1 += (dy * 60.0 - self.vel.1) * 0.5;
    }

    fn has_vel(&self) -> bool {
        self.vel.0 * self.vel.0 + self.vel.1 * self.vel.1 >= 1.0
    }

    /// `applyDecay`: the speed shrinks to 0.75 per 1/60 s (by 0.75 once
    /// when the clock gives 0) and the position moves by it, rounded.
    fn apply_decay(&mut self, pos: &mut (f64, f64), tick: u64, step: f64) {
        if self.touching {
            return;
        }
        if !self.has_vel() {
            self.vel = (0.0, 0.0);
            return;
        }
        self.clock.update(tick, step);
        let dt = self.clock.dt;
        let k = if dt == 0.0 { DECAY } else { DECAY.powf(60.0 * dt) };
        self.vel = (self.vel.0 * k, self.vel.1 * k);
        pos.0 = math_round(pos.0 + self.vel.0 * dt);
        pos.1 = math_round(pos.1 + self.vel.1 * dt);
    }
}

/// What the item's pictures are, in the gallery.
#[derive(Debug, Clone, Copy)]
pub struct DeskPics {
    pub outer: usize,
    pub page: usize,
    pub shadow: usize,
}

/// A paper on the desk.
pub struct DeskPaper {
    ent: EntId,
    outer: (f64, f64),
    inner: (f64, f64),
    dock: Dock,
    pics: DeskPics,
    /// The open page's marks (`innerVisuals`), in the page's coordinates.
    pub placed: Vec<Placed>,
    sounds: SoundSet,
    pub pos: (f64, f64),
    pub placement: Placement,
    pub state: State,
    pub dragging: bool,
    moved: bool,
    pub shadow: bool,
    drop_vel: f64,
    drag_start_placement: Placement,
    drag_offset: (f64, f64),
    drag_start: (f64, f64),
    drag_cur: (f64, f64),
    /// Where the press was, on the screen (`dragStartStagePos`).
    drag_start_stage: (f64, f64),
    touch: TouchDrag,
}

impl DeskPaper {
    /// A docking paper made by the booth (`Paper` constructor): its reveal
    /// is `DOCKED`, so it starts at its dock home, closed (`startRevealAnim`).
    pub fn docked(ent: EntId, outer: (f64, f64), inner: (f64, f64), dock: Dock, pics: DeskPics, placed: Vec<Placed>, sounds: SoundSet) -> DeskPaper {
        DeskPaper {
            ent,
            outer,
            inner,
            dock,
            pics,
            placed,
            sounds,
            pos: (dock.home[0], dock.home[1]),
            placement: Placement::Outer,
            state: State::Revealing,
            dragging: false,
            moved: false,
            shadow: false,
            drop_vel: 0.0,
            drag_start_placement: Placement::Outer,
            drag_offset: (0.0, 0.0),
            drag_start: (0.0, 0.0),
            drag_cur: (0.0, 0.0),
            drag_start_stage: (0.0, 0.0),
            touch: TouchDrag::default(),
        }
    }

    fn play(sound: &Option<String>, speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        if let Some(s) = sound {
            speaker.play(s, audio);
        }
    }

    fn set_placement(&mut self, p: Placement) {
        self.placement = p;
        self.shadow = false;
    }

    /// `clampPlacementPos` for an open page (a closed docking paper is
    /// held by its dock instead).
    fn clamp_inner(&mut self) {
        let r = BOOTH_INNER_CLAMP;
        let mx = if self.inner.0 >= 70.0 { 70.0 } else { self.inner.0 };
        let my = if self.inner.1 >= 30.0 { 30.0 } else { self.inner.1 };
        self.pos.0 = self.pos.0.max(r[0] - self.inner.0 + mx).min(r[0] + r[2] - mx);
        self.pos.1 = self.pos.1.max(r[1] - self.inner.1 + my).min(r[1] + r[3] - my);
    }

    /// `DockPoint.clampDrag` (entry `TOP`) on the closed paper's middle.
    fn dock_clamp(&self, (mut cx, mut cy): (f64, f64)) -> (f64, f64) {
        let (home, clamp) = (self.dock.home, self.dock.clamp);
        let (hw, hh) = (self.outer.0 * 0.5, self.outer.1 * 0.5);
        if clamp[1] + clamp[3] < cy + hh {
            if home[0] <= cx && cx <= home[0] + home[2] {
                let mid = (home[2] * 0.5 + home[0]).floor();
                let t = lerp_scale((cx - mid).abs() / hw, 0.5, 1.0, 0.0, 1.0);
                cx = mid;
                cy = cy.min(-hh * t + (home[3] * 0.5 + home[1]).floor());
            } else {
                cy = clamp[1] + clamp[3] - hh;
            }
        }
        cx = (clamp[0] + clamp[2] - hw).min((clamp[0] + hw).max(cx));
        cy = (clamp[1] + clamp[3] - hh).min((clamp[1] + hh).max(cy));
        (cx, cy)
    }

    /// `DockPoint.returnHome` (entry `TOP`), one frame: up above the home,
    /// across to it at 500 pixels a second, then down into it with gravity.
    /// True when it lands.
    fn return_home(&mut self, dt: f64, accel: f64) -> bool {
        let home = self.dock.home;
        let step = dt * 500.0;
        let (x, y) = &mut self.pos;
        if home[1] < *y {
            *y -= step;
            if *y <= home[1] {
                *y = home[1] - 1.0;
            }
        } else if (*x - home[0]).abs() > 0.001 {
            if *x < home[0] - 0.1 {
                *x = (step + *x).min(home[0]);
            } else if home[0] + 0.1 < *x {
                *x = (*x - step).max(home[0]);
            }
        } else if *y < home[1] {
            *y += (dt * (self.drop_vel + accel)).max(1.0);
            self.drop_vel += accel;
            if *y >= home[1] {
                *y = home[1];
                return true;
            }
        }
        false
    }

    /// `startCustomDrag`, `mouse` in booth coordinates.
    fn start_drag(&mut self, mouse: (f64, f64), stage: (f64, f64), speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        if self.state != State::Normal || self.dragging {
            return;
        }
        self.drag_start_placement = self.placement;
        self.dragging = true;
        self.moved = false;
        if self.placement == Placement::Outer {
            // Lifted to its home, 6 pixels up (entry TOP).
            self.pos = (self.dock.home[0], self.dock.home[1] - 6.0);
        }
        self.drag_offset = (mouse.0 - self.pos.0, mouse.1 - self.pos.1);
        self.drag_start = mouse;
        self.drag_cur = mouse;
        self.drag_start_stage = stage;
        self.touch.start(mouse);
        // `toTop` plays when the paper is already the last of the papers
        // (always while it is the only one).
        Self::play(&self.sounds.to_top, speaker, audio);
    }

    /// `updateCustomDrag`: the paper follows the pointer recorded in the
    /// last `react`.
    fn drag_to(&mut self, tick: u64, step: f64, speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        let (mx, my) = self.drag_cur;
        self.touch.update((mx, my), tick, step);
        let keep = |p: Placement| self.drag_start_placement == p;
        if mx >= BOOTH_INNER_X {
            let k = keep(Placement::Inner);
            self.set_placement(Placement::Inner);
            self.pos = if k { (mx - self.drag_offset.0, my - self.drag_offset.1) } else { (mx - self.inner.0 * 0.5, my - self.inner.1 * 0.5) };
            self.clamp_inner();
        } else {
            self.pos = if keep(Placement::Outer) {
                (mx - self.drag_offset.0, my - self.drag_offset.1)
            } else {
                (mx - self.outer.0 * 0.5, my - self.outer.1 * 0.5)
            };
            self.set_placement(Placement::Outer);
            let (hw, hh) = (self.outer.0 * 0.5, self.outer.1 * 0.5);
            let (cx, cy) = self.dock_clamp((self.pos.0 + hw, self.pos.1 + hh));
            self.pos = (cx - hw, cy - hh);
        }
        self.pos = (math_round(self.pos.0), math_round(self.pos.1));
        if !self.moved && cheb_floor(self.drag_cur, self.drag_start) > 1 {
            Self::play(&self.sounds.drag_start, speaker, audio);
            self.moved = true;
        }
        self.shadow = self.placement == Placement::Inner && self.moved;
    }

    /// `endCustomDrag`. A press that moved under 4 pixels is a click on the
    /// mark under the cursor: following its link comes in 4d.
    fn end_drag(&mut self, speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        self.dragging = false;
        if self.moved {
            Self::play(&self.sounds.drag_stop, speaker, audio);
        }
        self.moved = false;
        self.touch.touching = false;
        self.shadow = false;
        self.drop_vel = 0.0;
    }

    /// `DeskItem.update`, with the game's `dt`; `tick` counts every frame
    /// of the screen, shown or not (for TouchDrag's own clock).
    pub fn update(&mut self, dt: f64, tick: u64, speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        if self.dragging {
            self.drag_to(tick, dt, speaker, audio);
        }
        match self.state {
            // DOCKED: done on the first frame.
            State::Revealing => self.state = State::Normal,
            State::Normal if !self.dragging => match self.placement {
                Placement::Outer => {
                    if self.return_home(dt, dt * 3000.0) {
                        Self::play(&self.sounds.drop, speaker, audio);
                        Self::play(&self.sounds.drag_stop, speaker, audio);
                    }
                }
                Placement::Inner => {
                    if self.touch.has_vel() {
                        let mut pos = self.pos;
                        self.touch.apply_decay(&mut pos, tick, dt);
                        self.pos = pos;
                        self.clamp_inner();
                    }
                }
            },
            State::Normal => {}
        }
    }

    /// The shown sprite's clip rectangle, in the item's coordinates.
    fn local_clip(&self) -> [f64; 4] {
        match self.placement {
            Placement::Inner => clip_rect(self.pos, (0.0, 0.0), self.inner, &BOOTH_INNER_CLIP),
            Placement::Outer => clip_rect(self.pos, (0.0, 0.0), self.outer, &BOOTH_OUTER),
        }
    }

    /// `worldRect`, on the screen.
    fn world_rect(&self) -> Rect {
        let c = self.local_clip();
        [c[0] + self.pos.0, c[1] + self.pos.1 + BOOTH_Y, c[2], c[3]]
    }

    /// What is under a screen point: for an open page, a mark (by its index
    /// in `placed`) or the page itself (`Some(None)`); for a closed paper,
    /// the closed picture (`Some(None)` as well); else nothing.
    fn visual_at(&self, world: (f64, f64)) -> Option<Option<usize>> {
        let (lx, ly) = (world.0 - self.pos.0, world.1 - BOOTH_Y - self.pos.1);
        let clip = self.local_clip();
        match self.placement {
            Placement::Inner => {
                let page = hit_rect((0.0, 0.0), self.inner, &clip);
                if !inside(&page, lx, ly) {
                    return None;
                }
                let mut best: Option<(usize, [f64; 4])> = None;
                for (i, v) in self.placed.iter().enumerate() {
                    let r = hit_rect((v.x, v.y), (v.w as f64, v.h as f64), &clip);
                    if !inside(&r, lx, ly) {
                        continue;
                    }
                    if let Some((_, br)) = best {
                        if compare_proximity((lx, ly), &r, &br) > 0 {
                            continue;
                        }
                    }
                    best = Some((i, r));
                }
                Some(best.map(|(i, _)| i))
            }
            Placement::Outer => {
                let r = hit_rect((0.0, 0.0), self.outer, &clip);
                inside(&r, lx, ly).then_some(None)
            }
        }
    }

    /// `DeskItem.react`.
    pub fn react(&mut self, input: &mut Input, speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        let rect = self.world_rect();
        let mut held = false;
        if let Some(p) = input.pointer_over(self.ent, &rect) {
            let world = p.pos;
            let cursor = match self.visual_at(world) {
                None => Cursor::Arrow,
                Some(_) if self.placement == Placement::Outer => Cursor::Hand,
                Some(at) => {
                    let link = at.map(|i| self.placed[i].link.is_some()).unwrap_or(false);
                    if (!self.dragging || cheb_floor(world, self.drag_start_stage) < DRAG_CLICK_DIST) && link {
                        Cursor::Hand
                    } else {
                        Cursor::Arrow
                    }
                }
            };
            p.set_cursor(cursor);
            let (just_down, down) = (p.just_down, p.down);
            if down {
                p.capture(self.ent);
            }
            if just_down {
                self.start_drag((world.0, world.1 - BOOTH_Y), world, speaker, audio);
            }
            if down {
                self.drag_cur = (world.0, world.1 - BOOTH_Y);
                held = true;
            }
        }
        if self.dragging && !held {
            self.end_drag(speaker, audio);
        }
    }

    /// The item's quads: the drag shadow, the open page and its marks, or
    /// the closed picture, each with its clip rectangle. Positions are not
    /// rounded (a paper going home moves by fractions of a pixel).
    pub(crate) fn draw(&self, b: &mut Builder, gallery: &Gallery) {
        let (ox, oy) = (self.pos.0, self.pos.1 + BOOTH_Y);
        let to_screen = |c: [f64; 4]| [c[0] + ox, c[1] + oy, c[2], c[3]];
        let mut push = |image: usize, x: f64, y: f64, w: f64, h: f64, src: [i32; 4], color: u32, fade: f64, clip: [f64; 4]| {
            b.quads.push(Quad { image, x0: x, y0: y, x1: x + w, y1: y + h, src, color, fade, clip: Some(clip) });
        };
        let whole = |i: usize| {
            let p = &gallery.pictures[i];
            (p.width as f64, p.height as f64, [0, 0, p.width as i32, p.height as i32])
        };
        let clip = to_screen(self.local_clip());
        match self.placement {
            Placement::Inner => {
                if self.shadow {
                    let sc = to_screen(clip_rect(self.pos, SHADOW_OFFSET, self.inner, &BOOTH_INNER_CLIP));
                    let (w, h, src) = whole(self.pics.shadow);
                    push(self.pics.shadow, ox + SHADOW_OFFSET.0, oy + SHADOW_OFFSET.1, w, h, src, 0xFFFF_FFFF, SHADOW_ALPHA, sc);
                }
                let (w, h, src) = whole(self.pics.page);
                push(self.pics.page, ox, oy, w, h, src, 0xFFFF_FFFF, 1.0, clip);
                for v in &self.placed {
                    let (vx, vy) = (ox + v.x, oy + v.y);
                    match &v.visual {
                        Visual::Image(name) => {
                            if let Some(i) = gallery.picture(&format!("papers/{name}")) {
                                let (w, h, src) = whole(i);
                                push(i, vx, vy, w, h, src, 0xFFFF_FFFF, 1.0, clip);
                            }
                        }
                        Visual::Text { text, font: id } => {
                            let Some(f) = gallery.font(id) else { continue };
                            for tile in &text.build(f).tiles {
                                let image = tile.page.map_or(0, |p| gallery.sheet_index(&f.page_files[p]));
                                let (tx, ty) = (vx + tile.dst[0] as f64, vy + tile.dst[1] as f64);
                                push(image, tx, ty, tile.dst[2] as f64, tile.dst[3] as f64, tile.src, tile.color, 1.0, clip);
                            }
                        }
                    }
                }
            }
            Placement::Outer => {
                let (w, h, src) = whole(self.pics.outer);
                push(self.pics.outer, ox, oy, w, h, src, 0xFFFF_FFFF, 1.0, clip);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_page_keeps_70_by_30_pixels_on_the_desk() {
        let mut d = DeskPaper::docked(1, (26.0, 34.0), (246.0, 160.0), RULES_DOCK, DeskPics { outer: 0, page: 0, shadow: 0 }, Vec::new(), SoundSet::default());
        d.pos = (-500.0, 900.0);
        d.clamp_inner();
        assert_eq!(d.pos, (178.0 - 246.0 + 70.0, 217.0 - 30.0));
        d.pos = (900.0, -500.0);
        d.clamp_inner();
        assert_eq!(d.pos, (570.0 - 70.0, 0.0 - 160.0 + 30.0));
    }

    #[test]
    fn the_rulebook_held_closed_stays_above_the_clamp_bottom() {
        let d = DeskPaper::docked(1, (26.0, 34.0), (246.0, 160.0), RULES_DOCK, DeskPics { outer: 0, page: 0, shadow: 0 }, Vec::new(), SoundSet::default());
        // Over its own dock: held with its bottom at y 178.
        assert_eq!(d.dock_clamp((126.0, 185.0)), (126.0, 161.0));
        // Elsewhere: the same bottom, and inside x 0..570.
        assert_eq!(d.dock_clamp((5.0, 300.0)), (13.0, 161.0));
    }

    #[test]
    fn the_way_home_rises_slides_and_drops() {
        let mut d = DeskPaper::docked(1, (26.0, 34.0), (246.0, 160.0), RULES_DOCK, DeskPics { outer: 0, page: 0, shadow: 0 }, Vec::new(), SoundSet::default());
        let dt = 1.0 / 60.0;
        d.pos = (47.0, 74.0);
        let mut frames = 0;
        while !d.return_home(dt, dt * 3000.0) {
            frames += 1;
            assert!(frames < 100);
        }
        assert_eq!(d.pos, (113.0, 174.0));
        assert!(frames > 8, "it slides across at 500 pixels a second first");
    }

    #[test]
    fn a_thrown_page_slows_down_and_stops() {
        let mut t = TouchDrag::default();
        t.start((0.0, 0.0));
        let step = 1.0 / 60.0;
        t.update((0.0, 0.0), 1, step);
        t.update((10.0, 0.0), 2, step); // 600 px/s, smoothed by half
        assert_eq!(t.vel, (300.0, 0.0));
        t.touching = false;
        let mut pos = (100.0, 0.0);
        t.apply_decay(&mut pos, 3, step);
        assert_eq!(pos, (math_round(100.0 + 225.0 * step), 0.0));
        let mut n = 0;
        while t.has_vel() {
            n += 1;
            t.apply_decay(&mut pos, 3 + n, step);
        }
        assert!(n < 40 && pos.0 > 104.0);
    }

    #[test]
    fn the_inner_mark_inside_the_other_wins() {
        let big = [0.0, 0.0, 20.0, 20.0];
        let small = [5.0, 5.0, 4.0, 4.0];
        assert_eq!(compare_proximity((6.0, 6.0), &small, &big), -1);
        assert_eq!(compare_proximity((6.0, 6.0), &big, &small), 1);
    }
}
