//! The day screen (`play.screen.DayScreen`) as milestone 4a builds it: the
//! booth at the start of a day and the border scene's background and
//! booth button (docs/booth-screen.md, docs/milestone-4.md, "4a").
//! scripts/reference/boothscreen.py runs the same frames; tests/day.rs
//! compares the two.
//!
//! A day opens on a black card over the booth with the long date typing in
//! the middle. A figure walks in at the border (not drawn yet: only its
//! distance is kept); when it arrives, the booth plays `booth-intro` and
//! the card falls away over a second with a small bounce, and the border's
//! booth button starts blinking.
//!
//! Not here yet: the border's figures (milestone 6), the day's papers and
//! every click (4b), the booth's rules and travelers (milestone 5).

use std::f64::consts::PI;

use crate::aud::{AudioHost, Speaker};
use crate::button::{Background, Button, Look};
use crate::gdate;
use crate::pages::{Builder, Gallery};
use crate::picture::{Affine, Picture};
use crate::raster::Quad;
use crate::reveal_text::RevealText;
use crate::stater::{Curve, Host, Stater, Value, When};

/// The day screen asks for no song.
pub const SONG: Option<&str> = None;

/// Desktop layout values (docs/booth-layout.md).
const BOOTH_Y: f64 = 103.0;
const BOOTH_W: f64 = 570.0;
const BOOTH_H: f64 = 217.0;
const WALL_H: f64 = 107.0;
const COUNTER_Y: f64 = 105.0;
const CONSOLE_Y: f64 = 166.0;
const DESK_X: f64 = 178.0;
const DESK_W: f64 = 392.0;
const DESK_H: f64 = 217.0;
const SHUTTER_SWITCH: (f64, f64) = (150.0, 4.0);
const STAMP_BAR: (f64, f64) = (570.0, 24.0);
const CONSOLE_CLOCK: (f64, f64) = (9.0, 21.0);
const CONSOLE_DATE: (f64, f64) = (4.0, 48.0);
const CONSOLE_COUNT: (f64, f64) = (86.0, 42.0);
const OUTER_BOOTH_BUTTON: (f64, f64) = (146.0, 65.0);
const BORDER_H: i32 = 103;

/// `ConsoleEnt`'s static colours, the desk hint's, the shutter's shadow.
const DATE_COLOR: u32 = 0xFF42_2A1C;
const COUNT_COLOR: u32 = 0xFF6A_522F;
const HINT_COLOR: u32 = 0xFF32_2525;
const HINT_BACK: u32 = 0xFF19_1212;
const SHADOW_COLOR: u32 = 0xFF19_1212;
/// The opening card's text colour: white with alpha 0 (the typing sets it).
const CARD_TEXT: u32 = 0xFF_FFFF;

/// The walk-in figure's path `enter-right` (60 units) at the default speed.
const WALK_LENGTH: f64 = 60.0;
const WALK_SPEED: f64 = 10.0;

/// An `app.Clock` with the fixed step: its first update gives no time.
#[derive(Debug, Clone, Copy, Default)]
struct SubClock {
    started: bool,
    dt: f64,
}

impl SubClock {
    fn update(&mut self, frame_dt: f64) {
        self.dt = if self.started { frame_dt } else { 0.0 };
        self.started = true;
    }
}

/// What the booth's states move and run.
#[derive(Debug, Clone, Copy, PartialEq)]
enum BoothProp {
    CardActive,
    CardY,
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum BoothFunc {
    /// `off` (constructor lines 381, 385, 389).
    InputOff,
    StepReveal,
    InputOn,
    /// `intro` (399, 403).
    PlayIntro,
    HideCardText,
}

/// The booth's parts its states touch.
struct BoothParts {
    card_active: bool,
    card_y: f64,
    reveal: RevealText,
    /// The booth's switch 8 (its parts get input).
    parts_input: bool,
}

struct BoothCtx<'a> {
    parts: &'a mut BoothParts,
    dt: f64,
    speaker: &'a mut Speaker,
    audio: &'a mut dyn AudioHost,
}

impl Host<BoothProp, BoothFunc> for BoothCtx<'_> {
    fn get(&self, prop: BoothProp) -> Value {
        match prop {
            BoothProp::CardActive => Value::Bool(self.parts.card_active),
            BoothProp::CardY => Value::Num(self.parts.card_y),
        }
    }

    fn set(&mut self, prop: BoothProp, value: Value) {
        match (prop, value) {
            (BoothProp::CardActive, Value::Bool(b)) => self.parts.card_active = b,
            (BoothProp::CardY, Value::Num(y)) => self.parts.card_y = y,
            _ => {}
        }
    }

    fn run(&mut self, func: BoothFunc) {
        match func {
            BoothFunc::InputOff => self.parts.parts_input = false,
            BoothFunc::InputOn => self.parts.parts_input = true,
            BoothFunc::StepReveal => {
                self.parts.reveal.step_reveal(self.dt, self.speaker, self.audio);
            }
            BoothFunc::PlayIntro => {
                self.speaker.play("booth-intro", self.audio);
            }
            BoothFunc::HideCardText => self.parts.reveal.visible = false,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum BorderFunc {
    /// `ready-to-call` (border constructor lines 272, 276).
    ButtonInputOn,
    Blink,
}

struct BorderCtx<'a> {
    button: &'a mut Button,
    time: f64,
}

impl Host<(), BorderFunc> for BorderCtx<'_> {
    fn get(&self, _: ()) -> Value {
        Value::Bool(false)
    }
    fn set(&mut self, _: (), _: Value) {}
    fn run(&mut self, func: BorderFunc) {
        match func {
            BorderFunc::ButtonInputOn => self.button.enabled = true,
            // The tutorial's block is phone only.
            BorderFunc::Blink => self.button.set_look(if 0.375 < self.time % 0.75 { "normal" } else { "highlight" }),
        }
    }
}

/// `ConsoleClock.set_hour`: the clock's 16 x 16 picture (docs/booth-screen.md).
fn clock_picture(pin: &Picture, hour: f64) -> Picture {
    let size = 16.0;
    let rgba = |c: u32| [(c >> 16) as u8, (c >> 8) as u8, c as u8, (c >> 24) as u8];
    let dark = hour >= 18.0 || (hour > 16.0 && (hour * 20.0) % 1.0 > 0.75);
    let mut pic = Picture::filled(16, 16, if dark { rgba(DATE_COLOR) } else { [0; 4] });
    let hand = Picture::filled(32, 16, rgba(DATE_COLOR));
    let (hw, hh) = (hand.width as f64, hand.height as f64);
    let minute = hour % 1.0;
    let a_min = PI * 0.5 - (PI + PI) * minute;
    let a_hour = PI * 0.5 - (PI + PI) * (hour / 12.0);
    for (length, thick, angle) in [(size * 0.5 / hw, 1.0 / hh, a_min), (size * 0.5 * 0.75 / hw, 2.0 / hh, a_hour)] {
        let mut m = Affine::identity();
        m.translate(0.0, -hh * 0.5).scale(length, thick);
        let (c, s) = ((-angle).cos(), (-angle).sin());
        m.then([c, -s, 0.0, s, c, 0.0]).translate(size * 0.5, size * 0.5);
        pic.draw_affine(&hand, &m);
    }
    for y in 0..pin.height {
        for x in 0..pin.width {
            pic.set(7 + x, 7 + y, pin.texel(x, y));
        }
    }
    pic
}

/// Picture indexes the screen draws.
struct Pics {
    shutter: usize,
    counter: usize,
    console_under: usize,
    console: usize,
    switch_down: usize,
    desk: usize,
    bar_top: usize,
    bar_mid: usize,
    bar_bot: usize,
    background: usize,
    clock: usize,
}

pub struct DayScreen {
    booth: Stater<BoothProp, BoothFunc>,
    parts: BoothParts,
    booth_clock: SubClock,
    border: Stater<(), BorderFunc>,
    border_clock: SubClock,
    outer_booth: Button,
    shutter_switch: Button,
    /// The walk-in figure's distance along its path.
    walk: f64,
    walk_done: bool,
    /// The console's weight (none until the first update) and its text.
    weight: Option<String>,
    weight_text: String,
    date_text: String,
    hint: String,
    border_ambient: u32,
    booth_ambient: u32,
    pics: Pics,
    /// The frame count since the screen was made, for the tests.
    frames: u32,
    start_intro: Option<u32>,
}

impl DayScreen {
    /// The `DayScreen` constructor for story day 1: the booth, then the
    /// border scene. `dt` is this frame's time (the card types once).
    pub fn new(gallery: &mut Gallery, dt: f64, speaker: &mut Speaker, audio: &mut dyn AudioHost) -> Result<DayScreen, String> {
        let pic = |g: &Gallery, f: &str| g.picture(f).ok_or_else(|| format!("{f} is missing from the pack"));
        let pin = pic(gallery, "ClockPin.png")?;
        let pin_picture = gallery.pictures[pin].clone();
        let clock = gallery.made_picture("clock-6", |_| Ok(clock_picture(&pin_picture, 6.0)))?;
        let pics = Pics {
            shutter: pic(gallery, "Shutter.png")?,
            counter: pic(gallery, "Counter.png")?,
            console_under: pic(gallery, "ConsoleUnder.png")?,
            console: pic(gallery, "Console.png")?,
            switch_down: pic(gallery, "ShutterSwitchDown.png")?,
            desk: pic(gallery, "Desk.png")?,
            bar_top: pic(gallery, "StampBarTop.png")?,
            bar_mid: pic(gallery, "StampBarMid.png")?,
            bar_bot: pic(gallery, "StampBarBot.png")?,
            background: pic(gallery, "CheckpointBack.png")?,
            clock,
        };
        let switch_up = pic(gallery, "ShutterSwitchUp.png")?;
        let outer = pic(gallery, "OuterBooth.png")?;
        for f in ["title_tall", "ui_regular", "digits"] {
            gallery.font(f).ok_or_else(|| format!("font {f} is missing"))?;
        }
        let text = |id: &str| gallery.strings.get(id).cloned();
        let long_date = gdate::verbose(gdate::DAY1, text)?;
        let hint = text("booth_dragdocs").ok_or("text booth_dragdocs is missing from the pack")?;

        // The shutter starts closed at once: its enter function plays
        // `shutter-drop`, which the screen change's frame ignores, and its
        // switch is not set yet.
        speaker.play("shutter-drop", audio);
        let whole = |i: usize| Background::Piece { image: i, src: [0, 0, gallery.pictures[i].width as i32, gallery.pictures[i].height as i32] };
        let mut shutter_switch = Button::new("shutter-switch", 3, "", Look::new("down", whole(pics.switch_down), whole(pics.switch_down)));
        shutter_switch.looks.push(Look::new("up", whole(switch_up), whole(switch_up)));
        shutter_switch.x = SHUTTER_SWITCH.0;
        shutter_switch.y = SHUTTER_SWITCH.1;
        shutter_switch.enabled = false;

        // The opening card: the long date and a line break (a story day's
        // title is the empty text, not missing).
        let font = gallery.font("title_tall").unwrap();
        let mut reveal = RevealText::new();
        reveal.set_color(CARD_TEXT, font);
        reveal.set_text(&format!("{long_date}\n"), font);
        reveal.label.multi_line = true;
        reveal.set_color(CARD_TEXT, font);
        reveal.x = (BOOTH_W * 0.5 - reveal.width() as f64 * 0.5).floor();
        reveal.y = (BOOTH_H * 0.5 - reveal.height() as f64 * 0.5 - 20.0).floor();
        reveal.step_reveal(dt, speaker, audio);
        let date_text = gdate::format(gdate::DAY1, "%y.%m.%d");
        let border_ambient = speaker.play("border-ambient", audio);
        let booth_ambient = speaker.play("booth-ambient", audio);
        speaker.set_volume(border_ambient, 0.0, false);
        speaker.set_volume(booth_ambient, 0.0, false);

        let mut booth = Stater::new();
        booth
            .add("off")
            .func(When::Enter, BoothFunc::InputOff)
            .func(When::Step, BoothFunc::StepReveal)
            .func(When::Exit, BoothFunc::InputOn)
            .target(BoothProp::CardActive, Value::Bool(true), Curve::Plain)
            .target(BoothProp::CardY, Value::Num(0.0), Curve::Plain);
        booth
            .add("intro")
            .interp(1.0)
            .duration(0.0, "empty")
            .func(When::Enter, BoothFunc::PlayIntro)
            .func(When::Exit, BoothFunc::HideCardText)
            .target(BoothProp::CardActive, Value::Bool(false), Curve::Step(1.0))
            .target(BoothProp::CardY, Value::Num(BOOTH_H), Curve::Bounceback(0.2, 1));
        booth.add("empty").target(BoothProp::CardActive, Value::Bool(false), Curve::Plain);
        let mut parts = BoothParts { card_active: true, card_y: 0.0, reveal, parts_input: true };
        booth.go("off", true, &mut BoothCtx { parts: &mut parts, dt, speaker, audio });

        // The border scene: its booth button (no pressed picture), then
        // its states; the walk-in figure sets off.
        let band = BORDER_H - OUTER_BOOTH_BUTTON.1 as i32;
        let piece = |row: i32| Background::Piece { image: outer, src: [0, row, 56, band] };
        let mut outer_booth = Button::new("outer-booth", 4, "", Look::new("normal", piece(0), piece(0)));
        outer_booth.looks.push(Look::new("highlight", piece(band), piece(band)));
        outer_booth.x = OUTER_BOOTH_BUTTON.0;
        outer_booth.y = OUTER_BOOTH_BUTTON.1;
        outer_booth.enabled = false;
        let mut border = Stater::new();
        border.add("off");
        border.add("ready-to-call").func(When::Enter, BorderFunc::ButtonInputOn).func(When::Step, BorderFunc::Blink);
        border.go("off", true, &mut BorderCtx { button: &mut outer_booth, time: 0.0 });

        Ok(DayScreen {
            booth,
            parts,
            booth_clock: SubClock::default(),
            border,
            border_clock: SubClock::default(),
            outer_booth,
            shutter_switch,
            walk: 0.0,
            walk_done: false,
            weight: None,
            weight_text: "---".into(),
            date_text,
            hint,
            border_ambient,
            booth_ambient,
            pics,
            frames: 0,
            start_intro: None,
        })
    }

    /// The booth's state (`off`, `intro`, `empty`).
    pub fn booth_state(&self) -> &'static str {
        self.booth.current()
    }

    pub fn border_state(&self) -> &'static str {
        self.border.current()
    }

    /// Whether the opening card is shown, and its y inside the booth.
    pub fn card(&self) -> (bool, f64) {
        (self.parts.card_active, self.parts.card_y)
    }

    /// How many of the date's letters are out (spaces count).
    pub fn shown(&self) -> usize {
        self.parts.reveal.shown()
    }

    /// The border's booth button's look.
    pub fn button_look(&self) -> &str {
        &self.outer_booth.looks[self.outer_booth.current].name
    }

    /// The frame (counted from the screen's first) of `start-intro`.
    pub fn start_intro(&self) -> Option<u32> {
        self.start_intro
    }

    /// One frame: `Booth.update` (its clock, its states, the console, the
    /// ambient loops), then `Border.update` (its clock, its states, the
    /// walk-in figure). `time` is the game clock's time.
    pub fn update(&mut self, dt: f64, time: f64, speaker: &mut Speaker, audio: &mut dyn AudioHost) {
        self.frames += 1;
        self.booth_clock.update(dt);
        self.booth.step(self.booth_clock.dt, &mut BoothCtx { parts: &mut self.parts, dt, speaker, audio });
        // No traveler stands at his place: the weight is empty (which
        // clears the constructor's "---" on the first update).
        let weight = String::new();
        if self.weight.as_ref() != Some(&weight) {
            self.weight_text = weight.replace("kg", "");
            self.weight = Some(weight);
        }
        // `off`, `intro` and `empty` are border states: its sound, no room.
        speaker.set_volume(self.border_ambient, 1.0, true);
        speaker.set_volume(self.booth_ambient, 0.0, true);
        speaker.set_room(None);

        self.border_clock.update(dt);
        self.border.step(self.border_clock.dt, &mut BorderCtx { button: &mut self.outer_booth, time });
        if !self.walk_done {
            self.walk += self.border_clock.dt * WALK_SPEED;
            if self.walk >= WALK_LENGTH {
                self.walk_done = true;
                self.start_intro = Some(self.frames);
                // Border.person_onEvent("start-intro"): the booth's intro
                // (not instant: the first traveler is not the secret
                // police), then `ready-to-call`.
                self.booth.go("intro", false, &mut BoothCtx { parts: &mut self.parts, dt, speaker, audio });
                self.border.go("ready-to-call", false, &mut BorderCtx { button: &mut self.outer_booth, time });
            }
        }
    }

    /// The frame's quads: the shutter's shadow (layer -1), then the booth's
    /// parts in their order, then the border scene.
    pub fn quads(&self, gallery: &Gallery) -> Vec<Quad> {
        let mut b = Builder { gallery, quads: Vec::new() };
        let by = BOOTH_Y;
        // The shutter, at x -1, closed: openT 0.
        b.fill(-1.0, by, 180.0, WALL_H, SHADOW_COLOR);
        let strip_h = 20.0;
        let top = (-40.0 - WALL_H) * 0.0 + WALL_H;
        for i in 0..6 {
            let y = (f64::min(i as f64 * (WALL_H / 6.0), top - (6 - i) as f64 * strip_h * 0.5 - strip_h * 0.5)).floor() as i32;
            b.part(self.pics.shutter, -1.0, by + y as f64, [0, 20 * i, 180, 20]);
        }
        let whole = |b: &mut Builder, i: usize, x: f64, y: f64| {
            let p = &gallery.pictures[i];
            b.part(i, x, y, [0, 0, p.width as i32, p.height as i32]);
        };
        whole(&mut b, self.pics.counter, 0.0, by + COUNTER_Y);
        whole(&mut b, self.pics.console_under, 0.0, by + CONSOLE_Y);
        self.shutter_switch.draw(&mut b, gallery, (0.0, by));
        whole(&mut b, self.pics.desk, DESK_X, by);
        let ui = gallery.font("ui_regular").unwrap();
        let mut t = crate::text::Text::new(&self.hint);
        t.color = HINT_COLOR;
        let plain = t.build(ui);
        let hx = ((DESK_W * 0.5 + DESK_X).floor() - plain.width as f64 * 0.5).floor();
        let hy = (DESK_H - 5.0) - plain.height as f64;
        b.text(ui, &self.hint, hx, by + hy, |t| {
            t.color = HINT_COLOR;
            t.background = HINT_BACK;
            t.padding_x = 6;
            t.padding_y = 2;
        });
        // The console, moved to the end of the booth's children then.
        let cy = by + CONSOLE_Y;
        whole(&mut b, self.pics.console, 0.0, cy);
        whole(&mut b, self.pics.clock, CONSOLE_CLOCK.0, cy + CONSOLE_CLOCK.1);
        let digits = gallery.font("digits").unwrap();
        b.text(digits, &self.date_text, CONSOLE_DATE.0, cy + CONSOLE_DATE.1 - digits.ascent as f64, |t| t.color = DATE_COLOR);
        b.text(digits, "00", CONSOLE_COUNT.0, cy + CONSOLE_COUNT.1 - digits.ascent as f64 + digits.cap_height as f64, |t| {
            t.color = COUNT_COLOR
        });
        // The weight is empty in 4a: nothing to draw.
        debug_assert!(self.weight_text.is_empty() || self.weight.is_none());
        // The stamp bar, closed: 10 pixels show at the desk's right edge.
        let (bx, sy) = (STAMP_BAR.0 - 10.0, by + STAMP_BAR.1);
        let top_h = gallery.pictures[self.pics.bar_top].height as f64;
        let mid_h = gallery.pictures[self.pics.bar_mid].height as f64;
        whole(&mut b, self.pics.bar_top, bx, sy);
        whole(&mut b, self.pics.bar_bot, bx, sy + top_h + mid_h);
        whole(&mut b, self.pics.bar_mid, bx, sy + top_h);
        // The opening card.
        if self.parts.card_active {
            let gy = by + self.parts.card_y;
            b.fill(0.0, gy, BOOTH_W, BOOTH_H, 0xFF00_0000);
            if self.parts.reveal.visible {
                self.parts.reveal.draw(&mut b, gallery.font("title_tall").unwrap(), (0.0, gy));
            }
        }
        // The border scene: its background, then the booth button.
        whole(&mut b, self.pics.background, 0.0, 0.0);
        self.outer_booth.draw(&mut b, gallery, (0.0, 0.0));
        b.quads
    }
}
