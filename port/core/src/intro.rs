//! The page player (`play.screen.Intro`) and the intro screen
//! (`play.screen.IntroScreen`), docs/screens.md part 5 and
//! docs/milestone-3.md, 3c. scripts/reference/introscreen.py plays the same
//! run frame by frame; port/core/tests/intro.rs compares the two.
//!
//! A page: its picture is uncovered from the right over 1 s, then its
//! caption types on, then NEXT shows. From the second page on, a press
//! anywhere shows the page whole at once (the intro only; endings do not
//! allow it). After the last page's NEXT the screen around the player
//! decides what comes next.
//!
//! Not here yet: pages with a `when` condition and `$fact` values need the
//! story's facts (the intro has neither; endings come in milestone 9), and
//! the pause (milestone 3d).

use crate::aud::{AudioHost, Speaker};
use crate::button::{Background, Button, Look};
use crate::input::{EntId, Input};
use crate::num::{lerp_scale, math_round};
use crate::pages::{Builder, Gallery};
use crate::raster::Quad;
use crate::reveal_text::RevealText;
use crate::screen::{HEIGHT, WIDTH};
use crate::xmlscan;

/// The song the intro screen asks for.
pub const SONG: &str = "Theme";

/// Desktop places (docs/screens.md part 5, "Layout"): the pictures' top,
/// the caption's centre line, its wrapping width, NEXT's top.
const IMAGE_Y: i32 = 32;
const TEXT_CENTER_Y: f64 = 227.0;
const TEXT_WIDTH: i32 = 380;
const FOOTER_Y: f64 = 290.0;
/// The wipe's length, and how long after a page starts its sound plays.
const WIPE: f64 = 1.0;
const SOUND_DELAY: f64 = 2.0;
/// The caption's colour when a page gives none: white with alpha 0 (the
/// letters get their alpha from the typing).
const WHITE: u32 = 0xFF_FFFF;
const PUSH_ROWS: i32 = 19;
const GREEN: u32 = 0x55_6855;
/// The parts that ask for the pointer.
const PLAYER_ENT: EntId = 1;
const NEXT_ENT: EntId = 2;

/// One `<page>` of `Intro.xml` or `Ends.xml`.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct Page {
    pub image: Option<String>,
    pub text: Option<String>,
    pub color: Option<String>,
    pub sound: Option<String>,
    pub when: Option<String>,
}

/// The `<page>` entries of a file, in order.
pub fn read_pages(xml: &str) -> Vec<Page> {
    xmlscan::tags(xml)
        .into_iter()
        .filter(|t| t.name == "page")
        .map(|t| Page {
            image: t.attr("image").map(String::from),
            text: t.attr("text").map(String::from),
            color: t.attr("color").map(String::from),
            sound: t.attr("sound").map(String::from),
            when: t.attr("when").map(String::from),
        })
        .collect()
}

/// Haxe's `Std.parseInt` for a page's colour: `0x` and hex digits, or
/// decimal digits; a bad number counts as 0 (the caller's `toInt` of null).
fn parse_color(s: &str) -> u32 {
    let s = s.trim();
    let (digits, radix) = match s.strip_prefix("0x").or_else(|| s.strip_prefix("0X")) {
        Some(hex) => (hex, 16),
        None => (s, 10),
    };
    let end = digits.find(|c: char| !c.is_digit(radix)).unwrap_or(digits.len());
    i64::from_str_radix(&digits[..end], radix).map_or(0, |v| v as u32)
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    /// The page is being shown: the wipe, then the typing. NEXT hidden.
    Flipping,
    /// The page is up and NEXT shows.
    Idle,
}

/// An `app.vis.Sprite` picture holder. Without a picture its size is 0 x 0
/// (`Sprite.rebuild`), and it draws nothing.
#[derive(Debug, Clone)]
struct Holder {
    image: Option<usize>,
    size: (i32, i32),
    x: i32,
    y: i32,
    clip: Option<[i32; 4]>,
    visible: bool,
}

impl Holder {
    fn new() -> Holder {
        Holder { image: None, size: (0, 0), x: 0, y: IMAGE_Y, clip: None, visible: true }
    }

    fn draw(&self, b: &mut Builder) {
        if let (true, Some(image)) = (self.visible, self.image) {
            b.part_clipped(image, self.x, self.y, [0, 0, self.size.0, self.size.1], self.clip);
        }
    }
}

/// A page's sound waiting to play (`Tweener.timer`).
struct Timer {
    t: f64,
    sound: String,
}

/// `play.screen.Intro`.
pub struct PagePlayer {
    pages: Vec<Page>,
    allow_skip: bool,
    page_index: usize,
    state: State,
    /// The state's own clock (`stepTime`).
    step_time: f64,
    cur: Holder,
    nex: Holder,
    caption: RevealText,
    next: Button,
    timers: Vec<Timer>,
    /// Where this frame's wipe cut the pictures, for the tests.
    cut: Option<i32>,
}

impl PagePlayer {
    /// The constructor: everything placed, then `flipping` on the first
    /// page. `dt` is this frame's time: showing a page steps the caption
    /// once.
    pub fn new(gallery: &Gallery, pages: Vec<Page>, allow_skip: bool, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<PagePlayer, String> {
        gallery.font("title_tall").ok_or("font title_tall is missing")?;
        gallery.font("ui_large").ok_or("font ui_large is missing")?;
        let push = gallery.picture("PushButton.png").ok_or("PushButton.png is missing from the pack")?;
        let label = gallery.strings.get("menu_next").ok_or("text menu_next is missing from the pack")?;
        let push_w = gallery.pictures[push].width as i32;
        let look = Look::new(
            "normal",
            Background::Piece { image: push, src: [0, 0, push_w, PUSH_ROWS] },
            Background::Piece { image: push, src: [0, PUSH_ROWS, push_w, PUSH_ROWS] },
        )
        .with_text(label, GREEN, 0);
        let mut next = Button::new("next", NEXT_ENT, "ui_large", look);
        next.x = (WIDTH as f64 * 0.5 - push_w as f64 * 0.5).floor();
        next.y = FOOTER_Y;
        let mut caption = RevealText::new();
        caption.label.fixed_width = TEXT_WIDTH;
        caption.label.multi_line = true;
        caption.x = (WIDTH as f64 * 0.5 - TEXT_WIDTH as f64 * 0.5).floor();
        let mut player = PagePlayer {
            pages,
            allow_skip,
            page_index: 0,
            state: State::Flipping,
            step_time: 0.0,
            cur: Holder::new(),
            nex: Holder::new(),
            caption,
            next,
            timers: Vec::new(),
            cut: None,
        };
        player.enter(State::Flipping, gallery, dt, speaker, host)?;
        Ok(player)
    }

    pub fn page_index(&self) -> usize {
        self.page_index
    }

    pub fn state(&self) -> State {
        self.state
    }

    /// Where the wipe cut the pictures in the last update, if it ran.
    pub fn cut(&self) -> Option<i32> {
        self.cut
    }

    /// How many of the caption's letters are out (spaces count).
    pub fn shown(&self) -> usize {
        self.caption.shown()
    }

    pub fn next_visible(&self) -> bool {
        self.next.visible
    }

    /// `Stater.go` without a blend (neither state has one): the old state's
    /// exit, then the new one's.
    fn go(&mut self, to: State, gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<(), String> {
        if self.state == State::Flipping {
            self.end_page();
        }
        self.enter(to, gallery, dt, speaker, host)
    }

    /// `State.enter`: its clock from 0, its enter function, then its target
    /// (NEXT shown only in `idle`).
    fn enter(&mut self, to: State, gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<(), String> {
        self.state = to;
        self.step_time = 0.0;
        if to == State::Flipping {
            self.show_page(gallery, dt, speaker, host)?;
        }
        self.next.visible = to == State::Idle;
        Ok(())
    }

    /// `flipping`'s enter function: the caption gets the page's colour and
    /// text and is centred on its line, stepped once (which hides its
    /// letters), and the page's picture goes into the next holder.
    fn show_page(&mut self, gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<(), String> {
        if let Some(when) = self.pages.get(self.page_index).and_then(|p| p.when.as_ref()) {
            return Err(format!("a page with when=\"{when}\" needs the story's facts, which are not built yet"));
        }
        let Some(page) = self.pages.get(self.page_index).cloned() else { return Ok(()) };
        let font = gallery.font("title_tall").ok_or("font title_tall is missing")?;
        self.caption.set_text("", font);
        self.caption.set_color(page.color.as_deref().map_or(WHITE, parse_color), font);
        if let Some(sound) = page.sound {
            self.timers.push(Timer { t: 0.0, sound });
        }
        // `$name` is a story fact's text: none yet, so empty.
        let text = match page.text.as_deref() {
            Some(t) if t.starts_with('$') => String::new(),
            Some(t) => t.replace("&quote;", "\""),
            None => String::new(),
        };
        self.caption.set_text(&text, font);
        self.caption.x = (WIDTH as f64 * 0.5 - self.caption.width() as f64 * 0.5).floor();
        self.caption.y = (TEXT_CENTER_Y - self.caption.height() as f64 * 0.5).floor();
        self.caption.step_reveal(dt, speaker, host);
        // `$name` names the picture by a story fact: none yet, so the next
        // holder keeps what it has.
        if let Some(image) = page.image.filter(|i| !i.starts_with('$')) {
            let file = format!("intro/{image}");
            let index = gallery.picture(&file).ok_or_else(|| format!("{file} is missing from the pack"))?;
            self.nex.image = Some(index);
            self.nex.size = (gallery.pictures[index].width as i32, gallery.pictures[index].height as i32);
        }
        self.nex.x = (WIDTH as f64 * 0.5 - self.nex.size.0 as f64 * 0.5).floor() as i32;
        Ok(())
    }

    /// `flipping`'s exit function: the new picture becomes the current one,
    /// whole, and the whole caption shows.
    fn end_page(&mut self) {
        self.cur.image = self.nex.image;
        self.cur.size = self.nex.size;
        self.cur.x = (WIDTH as f64 * 0.5 - self.cur.size.0 as f64 * 0.5).floor() as i32;
        self.cur.clip = None;
        self.cur.visible = true;
        self.nex.visible = false;
        self.caption.reveal_all();
    }

    /// `flipping`'s step function: the wipe, a line from the current
    /// picture's right edge to its left over 1 s, the old picture left of
    /// it and the new one right of it; then, once past 1 s, the typing, and
    /// `idle` when no letter is left.
    fn wipe(&mut self, gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<(), String> {
        let t = lerp_scale(self.step_time, 0.0, WIPE, 0.0, 1.0);
        let left = self.cur.x as f64;
        let right = self.cur.size.0 as f64 + left;
        let cut = math_round((left - right) * t + right);
        self.cut = Some(cut);
        self.cur.clip = Some([0, 0, cut, 10000]);
        self.nex.clip = Some([cut, 0, 10000, 10000]);
        self.cur.visible = true;
        self.nex.visible = true;
        if WIPE < self.step_time && !self.caption.step_reveal(dt, speaker, host) {
            self.go(State::Idle, gallery, dt, speaker, host)?;
        }
        Ok(())
    }

    /// One frame: the page sounds' timers (the tree walk steps an entity's
    /// timed changes before its update), then the state's step, which adds
    /// the frame's time to its clock before its step function.
    pub fn update(&mut self, gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<(), String> {
        self.cut = None;
        self.timers.retain_mut(|timer| {
            if timer.t >= 1.0 {
                speaker.play(&timer.sound, host);
                false
            } else {
                timer.t = dt / SOUND_DELAY + timer.t;
                true
            }
        });
        self.step_time = dt + self.step_time;
        if self.state == State::Flipping {
            self.wipe(gallery, dt, speaker, host)?;
        }
        Ok(())
    }

    /// The input: NEXT first (the newest part), then the player's own
    /// `react`. True when NEXT was clicked after the last page (the
    /// player's "when done").
    pub fn react(&mut self, gallery: &Gallery, input: &mut Input, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<bool, String> {
        let mut done = false;
        if self.next.react((0.0, 0.0), input, speaker, host) {
            self.page_index += 1;
            if self.page_index >= self.pages.len() {
                done = true;
            } else {
                self.go(State::Flipping, gallery, dt, speaker, host)?;
            }
        }
        if self.allow_skip && self.page_index > 0 {
            let rect = [0.0, 0.0, WIDTH as f64, HEIGHT as f64];
            if let Some(p) = input.pointer_over(PLAYER_ENT, &rect) {
                let just_down = p.just_down;
                if p.down {
                    p.capture(PLAYER_ENT);
                }
                if just_down && self.state == State::Flipping {
                    // `endFlipNow`.
                    self.go(State::Idle, gallery, dt, speaker, host)?;
                }
            }
        }
        Ok(done)
    }

    /// Draws the current picture, the next one, the caption and NEXT.
    pub(crate) fn draw(&self, b: &mut Builder, gallery: &Gallery) {
        self.cur.draw(b);
        self.nex.draw(b);
        if let Some(font) = gallery.font("title_tall") {
            self.caption.draw(b, font, (0.0, 0.0));
        }
        self.next.draw(b, gallery, (0.0, 0.0));
    }
}

/// `play.screen.IntroScreen`: a black screen with a page player holding the
/// five pages of `Intro.xml`, hurrying allowed. The original then fades to
/// the day-1 newspaper; [`IntroScreen::react`] reports that the pages are
/// done and the game decides.
pub struct IntroScreen {
    pub player: PagePlayer,
}

impl IntroScreen {
    pub fn new(gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<IntroScreen, String> {
        let xml = gallery.data.get("Intro.xml").ok_or("data/Intro.xml is missing from the pack")?;
        let player = PagePlayer::new(gallery, read_pages(xml), true, dt, speaker, host)?;
        Ok(IntroScreen { player })
    }

    pub fn update(&mut self, gallery: &Gallery, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<(), String> {
        self.player.update(gallery, dt, speaker, host)
    }

    /// True once NEXT was clicked on the last page.
    pub fn react(&mut self, gallery: &Gallery, input: &mut Input, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Result<bool, String> {
        self.player.react(gallery, input, dt, speaker, host)
    }

    /// The quads, in drawing order: the black fill, then the player.
    pub fn quads(&self, gallery: &Gallery) -> Vec<Quad> {
        let mut b = Builder { gallery, quads: Vec::new() };
        b.fill(0.0, 0.0, WIDTH as f64, HEIGHT as f64, 0xFF00_0000);
        self.player.draw(&mut b, gallery);
        b.quads
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_pages_and_their_attributes() {
        let xml = r#"<end id="x"><page image="A.png" text="Hi &quot;you&quot;"/>
            <page image="B.png" sound="stamp-down" text="Two" when="End/X &gt;= 2"/>
            <page image="C.png" color="0xb19600" text="Three."/></end>"#;
        let pages = read_pages(xml);
        assert_eq!(pages.len(), 3);
        assert_eq!(pages[0].text.as_deref(), Some("Hi \"you\""));
        assert_eq!(pages[1].sound.as_deref(), Some("stamp-down"));
        assert_eq!(pages[1].when.as_deref(), Some("End/X >= 2"));
        assert_eq!(pages[2].color.as_deref(), Some("0xb19600"));
    }

    #[test]
    fn page_colours_parse_like_std_parse_int() {
        assert_eq!(parse_color("0xb19600"), 0xb19600);
        assert_eq!(parse_color("16777215"), 0xFF_FFFF);
        assert_eq!(parse_color("nonsense"), 0);
    }
}
