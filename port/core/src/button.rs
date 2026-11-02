//! `play.ui.Button` (docs/buttons.md): looks, the pressed state, the mouse
//! and shortcut-key rules of `ButtonHelper.react`, and drawing.

use crate::aud::{AudioHost, Speaker};
use crate::input::{Cursor, EntId, Input, Key, Rect};
use crate::pages::{Builder, Gallery};
use crate::text::{Align, Text};

/// A button's background picture: a piece of a picture, or (for pictures the
/// game makes at run time, like the title's credit bar) a filled box.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Background {
    Piece { image: usize, src: [i32; 4] },
    Fill { w: i32, h: i32, color: u32 },
}

impl Background {
    fn size(&self) -> (i32, i32) {
        match *self {
            Background::Piece { src, .. } => (src[2], src[3]),
            Background::Fill { w, h, .. } => (w, h),
        }
    }

    fn draw(&self, b: &mut Builder, x: f64, y: f64) {
        match *self {
            Background::Piece { image, src } => b.part(image, x, y, src),
            Background::Fill { w, h, color } => b.fill(x, y, w as f64, h as f64, color),
        }
    }
}

/// One way the button can appear (`play.ui.Mode`).
#[derive(Debug, Clone)]
pub struct Look {
    pub name: String,
    pub normal: Background,
    pub pressed: Background,
    pub text: String,
    pub normal_color: u32,
    pub pressed_color: u32,
    pub align: Align,
}

impl Look {
    /// `addMode(name, normal, pressed)`: no text, white text, centred.
    pub fn new(name: &str, normal: Background, pressed: Background) -> Look {
        Look {
            name: name.into(),
            normal,
            pressed,
            text: String::new(),
            normal_color: 0xFFFF_FFFF,
            pressed_color: 0xFFFF_FFFF,
            align: Align::Center,
        }
    }

    pub fn with_text(mut self, text: &str, normal: u32, pressed: u32) -> Look {
        self.text = text.into();
        self.normal_color = normal;
        self.pressed_color = pressed;
        self
    }
}

pub struct Button {
    pub id: String,
    /// Its number for the pointer questions.
    pub ent: EntId,
    pub font: String,
    /// Position inside its parent.
    pub x: f64,
    pub y: f64,
    pub looks: Vec<Look>,
    pub current: usize,
    pub pressing: bool,
    /// `buttonVisible`: hidden buttons are neither drawn nor clicked.
    pub visible: bool,
    /// The entity switch 4: without it the button gets no input and looks
    /// the same.
    pub enabled: bool,
    pub shortcut: Option<Key>,
    /// Left, right, top, bottom.
    pub margins: [f64; 4],
    pub press_sound: Option<String>,
    pub click_sound: Option<String>,
}

impl Button {
    /// `Button(parent, font, pressSound, clickSound)` with the defaults, and
    /// its first look (which becomes current).
    pub fn new(id: &str, ent: EntId, font: &str, look: Look) -> Button {
        Button {
            id: id.into(),
            ent,
            font: font.into(),
            x: 0.0,
            y: 0.0,
            looks: vec![look],
            current: 0,
            pressing: false,
            visible: true,
            enabled: true,
            shortcut: None,
            margins: [0.0; 4],
            press_sound: Some("button-down".into()),
            click_sound: Some("button-up".into()),
        }
    }

    /// `setAsBackButton`: Escape presses it.
    pub fn set_as_back_button(&mut self) {
        self.shortcut = Some(Key::Escape);
    }

    fn look(&self) -> &Look {
        &self.looks[self.current]
    }

    /// The background picture's size (every button the port makes so far
    /// has one).
    pub fn size(&self) -> (i32, i32) {
        self.look().normal.size()
    }

    /// `Button.react` and `ButtonHelper.react`, with the button's parent at
    /// `origin` on screen. True when clicked; the caller then runs what the
    /// click does (the button's `whenClick`).
    pub fn react(&mut self, origin: (f64, f64), input: &mut Input, speaker: &mut Speaker, host: &mut dyn AudioHost) -> bool {
        if !self.visible || !self.enabled {
            return false;
        }
        let (w, h) = self.size();
        let [ml, mr, mt, mb] = self.margins;
        let rect: Rect = [origin.0 + self.x - ml, origin.1 + self.y - mt, w as f64 + ml + mr, h as f64 + mt + mb];
        let was_pressing = self.pressing;
        let play = |sound: &Option<String>, speaker: &mut Speaker, host: &mut dyn AudioHost| {
            if let Some(s) = sound {
                speaker.play(s, host);
            }
        };
        let mut clicked = false;
        let mut use_mouse = true;
        if let Some(key) = self.shortcut {
            if !input.intersects_masked_area(&rect) {
                if input.key_down(key) {
                    // While the key is down the mouse is not looked at.
                    self.pressing = true;
                    if !was_pressing {
                        play(&self.press_sound, speaker, host);
                    }
                    use_mouse = false;
                } else if self.pressing && input.key_just_up(key) {
                    self.pressing = false;
                    play(&self.click_sound, speaker, host);
                    clicked = true;
                    use_mouse = false;
                }
            }
        }
        if use_mouse {
            match input.pointer_over(self.ent, &rect) {
                None => self.pressing = false,
                Some(p) => {
                    let (x, y) = p.pos;
                    let over = rect[0] <= x && x < rect[0] + rect[2] && rect[1] <= y && y < rect[1] + rect[3];
                    if over {
                        p.set_cursor(Cursor::Hand);
                    }
                    if !p.is_capturing(self.ent) && p.just_down {
                        play(&self.press_sound, speaker, host);
                        p.capture(self.ent);
                    }
                    if p.is_capturing(self.ent) {
                        self.pressing = p.down && over;
                        if p.down {
                            p.capture(self.ent);
                        } else if was_pressing && over {
                            play(&self.click_sound, speaker, host);
                            clicked = true;
                        }
                    }
                }
            }
        }
        clicked
    }

    /// Draws the button with its parent at `origin`: the background, then
    /// the text (always opaque; centred as `applyMode` places it).
    pub(crate) fn draw(&self, b: &mut Builder, gallery: &Gallery, origin: (f64, f64)) {
        if !self.visible {
            return;
        }
        let look = self.look();
        let background = if self.pressing { look.pressed } else { look.normal };
        let (x, y) = (origin.0 + self.x, origin.1 + self.y);
        background.draw(b, x, y);
        if look.text.is_empty() {
            return;
        }
        let Some(font) = gallery.font(&self.font) else { return };
        let color = 0xFF00_0000 | if self.pressing { look.pressed_color } else { look.normal_color };
        let mut t = Text::new(&look.text);
        t.align = look.align;
        let built = t.build(font);
        let (pw, ph) = background.size();
        let (tw, th) = (built.width as f64, built.height as f64);
        let tx = match look.align {
            Align::Left => 2.0,
            Align::Center => (pw as f64 * 0.5 - tw * 0.5).floor(),
            Align::Right => pw as f64 - tw - 2.0,
        };
        let ty = (ph as f64 * 0.5 - th * 0.5).floor();
        let align = look.align;
        b.text(font, &look.text, x + tx, y + ty, |t| {
            t.align = align;
            t.color = color;
        });
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::aud::sim::SimHost;
    use crate::aud::SoundDefs;
    use crate::input::{HostInput, KEY_COUNT};

    const SOUNDS: &str = r#"<sound id="button-down"/><sound id="button-up"/>"#;

    fn button() -> Button {
        let bg = Background::Fill { w: 20, h: 10, color: 0xFF00_0000 };
        let mut b = Button::new("b", 1, "ui_large", Look::new("normal", bg, bg));
        b.x = 100.0;
        b.y = 50.0;
        b
    }

    struct Rig {
        input: Input,
        speaker: Speaker,
        host: SimHost,
    }

    impl Rig {
        fn new() -> Rig {
            Rig { input: Input::new(), speaker: Speaker::new(SoundDefs::parse(SOUNDS).unwrap()), host: SimHost::new(&[]) }
        }

        /// One frame with the mouse at (x, y); true when the button clicked.
        fn frame(&mut self, b: &mut Button, x: f64, y: f64, down: bool) -> bool {
            let host = HostInput { keys: [false; KEY_COUNT], mouse_valid: true, mouse: (x, y), left_down: down };
            self.input.update(&host, 1.0 / 60.0);
            b.react((0.0, 0.0), &mut self.input, &mut self.speaker, &mut self.host)
        }

        fn sounds(&self) -> Vec<&str> {
            self.host.log.iter().filter_map(|l| l.split(' ').nth(3)).collect()
        }
    }

    #[test]
    fn press_then_let_go_over_it_clicks_with_both_sounds() {
        let (mut r, mut b) = (Rig::new(), button());
        assert!(!r.frame(&mut b, 105.0, 55.0, false));
        assert_eq!(r.input.pointer.cursor, Some(Cursor::Hand));
        assert!(!r.frame(&mut b, 105.0, 55.0, true));
        assert!(b.pressing);
        assert_eq!(r.sounds(), ["button-down.wav"], "the press sound on the press");
        assert!(r.frame(&mut b, 106.0, 55.0, false));
        assert!(!b.pressing);
        assert_eq!(r.sounds(), ["button-down.wav", "button-up.wav"]);
    }

    #[test]
    fn sliding_off_unpresses_and_letting_go_outside_does_nothing() {
        let (mut r, mut b) = (Rig::new(), button());
        r.frame(&mut b, 105.0, 55.0, true);
        r.frame(&mut b, 300.0, 55.0, true);
        assert!(!b.pressing, "off the button");
        r.frame(&mut b, 105.0, 55.0, true);
        assert!(b.pressing, "back on, still taken");
        r.frame(&mut b, 300.0, 55.0, true);
        assert!(!r.frame(&mut b, 300.0, 55.0, false));
        assert_eq!(r.sounds(), ["button-down.wav"]);
    }

    #[test]
    fn pressing_outside_and_sliding_on_does_not_press() {
        let (mut r, mut b) = (Rig::new(), button());
        r.frame(&mut b, 10.0, 10.0, true);
        r.frame(&mut b, 105.0, 55.0, true);
        assert!(!b.pressing);
        assert!(!r.frame(&mut b, 105.0, 55.0, false));
        assert!(r.sounds().is_empty());
    }

    #[test]
    fn the_right_and_bottom_edges_are_outside() {
        let (mut r, mut b) = (Rig::new(), button());
        r.frame(&mut b, 120.0, 55.0, false);
        assert_eq!(r.input.pointer.cursor, None);
        r.frame(&mut b, 119.0, 59.0, false);
        assert_eq!(r.input.pointer.cursor, Some(Cursor::Hand));
    }

    #[test]
    fn a_back_button_clicks_when_escape_is_let_go() {
        let (mut r, mut b) = (Rig::new(), button());
        b.set_as_back_button();
        let mut host = HostInput { mouse_valid: true, mouse: (400.0, 300.0), ..HostInput::default() };
        host.keys[Key::Escape as usize] = true;
        for _ in 0..3 {
            r.input.update(&host, 1.0 / 60.0);
            assert!(!b.react((0.0, 0.0), &mut r.input, &mut r.speaker, &mut r.host));
            assert!(b.pressing);
        }
        host.keys[Key::Escape as usize] = false;
        r.input.update(&host, 1.0 / 60.0);
        assert!(b.react((0.0, 0.0), &mut r.input, &mut r.speaker, &mut r.host));
        assert_eq!(r.sounds(), ["button-down.wav", "button-up.wav"]);
    }

    #[test]
    fn a_disabled_button_gets_no_input() {
        let (mut r, mut b) = (Rig::new(), button());
        b.enabled = false;
        r.frame(&mut b, 105.0, 55.0, true);
        assert!(!b.pressing);
        assert_eq!(r.input.pointer.cursor, None);
    }
}
