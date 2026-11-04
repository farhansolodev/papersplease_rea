//! `play.ui.RevealTextEnt`: a text whose letters appear one by one (the
//! intro and ending captions, later the night screen's messages;
//! docs/screens.md part 1, "Timed changes", and part 5). The whole text is
//! laid out at once, so it has its full size from the start; a letter is
//! shown by setting its tile's alpha to 1 (docs/text-drawing.md, "Letters
//! shown one by one"). scripts/reference/introscreen.py has the same rules.

use crate::aud::{AudioHost, Speaker};
use crate::font::Font;
use crate::pages::Builder;
use crate::text::{Built, Text};

/// The countdown before the first letter (`set_text`).
const FIRST_DELAY: f64 = 0.05;
/// After a full stop, after a comma, after any other letter.
const STOP_DELAY: f64 = 0.5;
const COMMA_DELAY: f64 = 0.25;
const LETTER_DELAY: f64 = 0.04;
/// The sound at every third letter.
const SOUND: &str = "text-reveal";

pub struct RevealText {
    /// The label (`app.vis.Text`), its position inside the parent.
    pub label: Text,
    pub x: f64,
    pub y: f64,
    built: Built,
    reveal_index: usize,
    reveal_countdown: f64,
    /// Each built letter's alpha, as its tile's colour holds it (a float).
    alpha: Vec<f32>,
}

impl RevealText {
    /// A new one (the constructor turns the built letters on). Its label
    /// has the game's defaults: no text, colour 0.
    pub fn new() -> RevealText {
        RevealText {
            label: Text::new(""),
            x: 0.0,
            y: 0.0,
            built: Built::empty(),
            reveal_index: 0,
            reveal_countdown: 0.0,
            alpha: Vec::new(),
        }
    }

    /// Lays the label out again, as `buildTiles` does when a setting
    /// changed: every tile gets the label's colour again, so the letters
    /// take its alpha until the next `step_reveal`.
    fn rebuild(&mut self, font: &Font) {
        self.built = self.label.build(font);
        let alpha = (self.label.color >> 24) as f32 / 255.0;
        self.alpha = vec![alpha; self.built.letters.len()];
    }

    /// `set_text`: the new text, no letter shown, the first one 0.05 s away.
    pub fn set_text(&mut self, text: &str, font: &Font) {
        self.label.text = text.to_string();
        self.rebuild(font);
        self.reveal_index = 0;
        self.reveal_countdown = FIRST_DELAY;
    }

    /// The label's `set_color`.
    pub fn set_color(&mut self, color: u32, font: &Font) {
        self.label.color = color;
        self.rebuild(font);
    }

    pub fn width(&self) -> i32 {
        self.built.width
    }

    pub fn height(&self) -> i32 {
        self.built.height
    }

    /// How many built letters are shown (spaces count).
    pub fn shown(&self) -> usize {
        self.alpha.iter().filter(|&&a| a >= 0.001).count()
    }

    /// `stepReveal`, with the game clock's frame time: false when every
    /// letter is already out. Otherwise the countdown loses `dt`; while it
    /// is below 0 the next letter comes out (the sound at every third), and
    /// the countdown gains that letter's delay; then every letter's alpha is
    /// set, 1 if out, else 0.
    pub fn step_reveal(&mut self, dt: f64, speaker: &mut Speaker, host: &mut dyn AudioHost) -> bool {
        let letters = &self.built.letters;
        if self.reveal_index >= letters.len() {
            return false;
        }
        self.reveal_countdown -= dt;
        if self.reveal_countdown < 0.0 {
            while self.reveal_index < letters.len() {
                if self.reveal_index % 3 == 0 {
                    speaker.play(SOUND, host);
                }
                let delay = match letters[self.reveal_index].0 {
                    '.' | '\u{3002}' => STOP_DELAY,
                    ',' | '\u{3001}' => COMMA_DELAY,
                    _ => LETTER_DELAY,
                };
                self.reveal_countdown = delay + self.reveal_countdown;
                self.reveal_index += 1;
                if self.reveal_countdown >= 0.0 {
                    break;
                }
            }
        }
        let shown = self.reveal_index;
        for (i, a) in self.alpha.iter_mut().enumerate() {
            *a = if i < shown { 1.0 } else { 0.0 };
        }
        true
    }

    /// `revealAll`: every letter shown. Its `text-reveal` (played when
    /// `revealIndex < revealCount`) never plays: nothing in the game sets
    /// `revealCount`, so it stays 0. The reveal index is left as it is.
    pub fn reveal_all(&mut self) {
        self.alpha.iter_mut().for_each(|a| *a = 1.0);
    }

    /// Draws the label with its parent at `origin`. A tile that is not a
    /// built letter (a missing letter's box) keeps the label's colour.
    pub(crate) fn draw(&self, b: &mut Builder, font: &Font, origin: (f64, f64)) {
        let mut alpha_of = vec![None; self.built.tiles.len()];
        for (letter, (_, tile)) in self.built.letters.iter().enumerate() {
            if let Some(t) = tile {
                alpha_of[*t] = Some(self.alpha[letter]);
            }
        }
        b.tiles(font, &self.built, origin.0 + self.x, origin.1 + self.y, |i, tile| match alpha_of[i] {
            Some(a) => ((a * 255.0) as u32) << 24 | (tile.color & 0xFF_FFFF),
            None => tile.color,
        });
    }
}

impl Default for RevealText {
    fn default() -> Self {
        Self::new()
    }
}
