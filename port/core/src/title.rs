//! The title screen (`play.screen.TitleScreen`, docs/screens.md part 2):
//! milestone 1b drew it as a still; since milestone 3a it is alive. The
//! title rises with `Theme`'s beat on the first title of the run, a click or
//! a key skips the rise, the logo bobs once a bar, and the buttons press and
//! click with their sounds (docs/buttons.md). Positions from screens.md part 2
//! and buttons.md; scripts/reference/titlescreen.py builds the same quads for
//! the screen at rest.
//!
//! Left out: the quit button (the user's decision), the version button (its
//! text is not read yet) and the test tooling's `SoakTapper`. What a click
//! leads to (the load, endless, settings and credits screens) comes with
//! later milestones; [`TitleScreen::react`] returns the clicked button's id.

use crate::aud::{AudioHost, Music, Speaker};
use crate::button::{Background, Button, Look};
use crate::input::Input;
use crate::num::{math_round, smoothstep};
use crate::pages::{Builder, Gallery};
use crate::raster::{Quad, Screen};
use crate::screen::{HEIGHT, WIDTH};

/// The desktop layout's values for this screen (docs/booth-layout.md).
const LOGO_TOP: f64 = 28.0;
const MENU_CENTER_Y: f64 = 260.0;
const MENU_ITEM_PADDING_Y: i32 = 10;
const NOTCH_HEIGHT: i32 = 0;
/// How far the corner buttons and the credit sit from the screen's edges.
const EDGE: f64 = 10.0;
/// Rows per state of `PushButton.png` and of the title's `SettingsButton.png`.
const PUSH_ROWS: i32 = 19;
const SETTINGS_ROWS: i32 = 29;
/// The credit's run-time pictures: 140 x 12, black, or green when pressed.
const CREDIT_SIZE: (i32, i32) = (140, 12);
/// A button text's colour (0x556855); pressed texts are black.
const GREEN: u32 = 0x55_6855;

/// `TitleScreen.update`'s numbers: b = beat x 0.5 + 0.035; the rise is 20
/// steps, each eased over its first fifth; the logo bobs 5 pixels.
const BEAT_SCALE: f64 = 0.5;
const BEAT_SHIFT: f64 = 0.035;
const RISE_STEPS: f64 = 20.0;
const RISE_EASE: f64 = 0.2;
const BOB: f64 = 5.0;

/// The song this screen asks for.
pub const SONG: &str = "Theme";

/// The top of each button of a menu's centre column (`Menu.applyCenterY`):
/// the column is at most the screen less the notch less 40 high, the space
/// left over is shared out per button (rounded down), and the column is
/// centred on `center_y`.
fn menu_column(heights: &[i32], center_y: f64) -> Vec<i32> {
    let total: i32 = heights.iter().sum();
    let n = heights.len() as i32;
    let height = f64::min(
        (HEIGHT as i32 - NOTCH_HEIGHT - 40) as f64,
        ((n - 1) * MENU_ITEM_PADDING_Y + total) as f64,
    );
    let gap = ((height - total as f64) / n as f64).floor() as i32;
    let mut y = (center_y - height * 0.5) as i32;
    heights
        .iter()
        .map(|h| {
            let top = y;
            y += h + gap;
            top
        })
        .collect()
}

/// Left (or top) of something `size` long centred in `room`, rounded down.
fn centred(room: f64, size: f64) -> f64 {
    (room * 0.5 - size * 0.5).floor()
}

/// A picture cut into two bands of `rows`: the upper normal, the lower
/// pressed (`Menu.addImageButton`, `GameScreen.makePushButton`).
fn banded(image: usize, width: i32, rows: i32) -> Look {
    Look::new(
        "normal",
        Background::Piece { image, src: [0, 0, width, rows] },
        Background::Piece { image, src: [0, rows, width, rows] },
    )
}

pub struct TitleScreen {
    /// The first title screen made since the start (only that one rises).
    first: bool,
    rising: bool,
    skipped: bool,
    /// The container holding the logo and the buttons: its top, which
    /// starts one screen height down.
    container_y: f64,
    logo: usize,
    logo_x: f64,
    logo_y: f64,
    /// The screen's switch 8: while it is off (the title rising) the
    /// buttons get no input.
    children_react: bool,
    buttons: Vec<Button>,
}

impl TitleScreen {
    /// The constructor. `first` is true for the first title of the run.
    /// Asking for the song is the screen change's job (`Music.play` with the
    /// screen's song, docs/audio-layer.md); see [`SONG`].
    pub fn new(gallery: &Gallery, first: bool) -> Result<TitleScreen, String> {
        let picture = |file: &str| gallery.picture(file).ok_or_else(|| format!("{file} is missing from the pack"));
        let string = |id: &str| gallery.strings.get(id).cloned().ok_or_else(|| format!("text {id} is missing from the pack"));
        for font in ["ui_large", "regular"] {
            gallery.font(font).ok_or_else(|| format!("font {font} is missing"))?;
        }
        let (logo, push, settings) = (picture("Title.png")?, picture("PushButton.png")?, picture("SettingsButton.png")?);
        let w = WIDTH as f64;

        let mut buttons = Vec::new();
        let push_w = gallery.pictures[push].width as i32;
        let x = centred(w, push_w as f64);
        let menu = [("story", string("menu_story")?), ("endless", string("menu_endless")?)];
        for ((id, label), top) in menu.iter().zip(menu_column(&[PUSH_ROWS; 2], MENU_CENTER_Y)) {
            let look = banded(push, push_w, PUSH_ROWS).with_text(label, GREEN, 0);
            let mut b = Button::new(id, buttons.len() as u32 + 1, "ui_large", look);
            (b.x, b.y) = (x, top as f64);
            buttons.push(b);
        }

        let settings_w = gallery.pictures[settings].width as i32;
        let mut b = Button::new("settings", 3, "ui_large", banded(settings, settings_w, SETTINGS_ROWS));
        (b.x, b.y) = (EDGE, HEIGHT as f64 - EDGE - SETTINGS_ROWS as f64);
        buttons.push(b);

        let (cw, ch) = CREDIT_SIZE;
        let look = Look::new(
            "normal",
            Background::Fill { w: cw, h: ch, color: 0xFF00_0000 },
            Background::Fill { w: cw, h: ch, color: 0xFF00_0000 | GREEN },
        )
        .with_text(&string("created_by")?, GREEN, 0);
        let mut b = Button::new("credit", 4, "regular", look);
        (b.x, b.y) = (centred(w, cw as f64), HEIGHT as f64 - ch as f64 - EDGE);
        buttons.push(b);

        let logo_w = gallery.pictures[logo].width as f64;
        Ok(TitleScreen {
            first,
            rising: first,
            skipped: false,
            container_y: HEIGHT as f64,
            logo,
            logo_x: centred(w, logo_w),
            logo_y: LOGO_TOP,
            children_react: true,
            buttons,
        })
    }

    /// Where the title rests once it has risen, with no song playing (so the
    /// logo does not bob): milestone 1b's still.
    pub fn at_rest(gallery: &Gallery) -> Result<TitleScreen, String> {
        let mut t = TitleScreen::new(gallery, false)?;
        t.container_y = 0.0;
        t.rising = false;
        Ok(t)
    }

    /// True while the title is still rising.
    pub fn rising(&self) -> bool {
        self.rising
    }

    /// The container's top (0 once the title has arrived).
    pub fn container_y(&self) -> f64 {
        self.container_y
    }

    /// The logo's top inside the container (28, or up to 5 lower while it
    /// bobs).
    pub fn logo_y(&self) -> f64 {
        self.logo_y
    }

    /// `TitleScreen.update`, every frame, from the music's beat.
    pub fn update(&mut self, music: &Music, speaker: &Speaker) {
        let beat = music.is_playing(speaker).then(|| music.beat(speaker));
        let rise = rise(beat, self.first && !self.skipped);
        self.rising = rise.rising;
        self.container_y = rise.container_y;
        if let Some(logo_y) = rise.logo_y {
            self.logo_y = logo_y;
        }
        self.children_react = !self.rising;
    }

    /// The buttons (topmost, the last added, first), then the screen's own
    /// `react`: while rising, any click or game key skips the rise and the
    /// mouse is held back until it is let go. Returns the id of a clicked
    /// button.
    pub fn react(&mut self, input: &mut Input, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Option<String> {
        let mut clicked = None;
        if self.children_react {
            let origin = (0.0, self.container_y);
            for b in self.buttons.iter_mut().rev() {
                if b.react(origin, input, speaker, host) && clicked.is_none() {
                    clicked = Some(b.id.clone());
                }
            }
        }
        if self.rising && (input.pointer.just_down || input.any_key_just_down()) {
            self.skipped = true;
            input.mask_all_pointers_until_release();
        }
        clicked
    }

    /// The quads, in drawing order.
    pub fn quads(&self, gallery: &Gallery) -> Vec<Quad> {
        let mut b = Builder { gallery, quads: Vec::new() };
        b.fill(0.0, 0.0, WIDTH as f64, HEIGHT as f64, 0xFF00_0000);
        let pic = &gallery.pictures[self.logo];
        let (w, h) = (pic.width as i32, pic.height as i32);
        b.part(self.logo, self.logo_x, self.container_y + self.logo_y, [0, 0, w, h]);
        for button in &self.buttons {
            button.draw(&mut b, gallery, (0.0, self.container_y));
        }
        b.quads
    }
}

/// What one frame of `TitleScreen.update` decides.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Rise {
    pub rising: bool,
    pub container_y: f64,
    /// The logo's new top inside the container; `None` leaves it.
    pub logo_y: Option<f64>,
}

/// `TitleScreen.update`'s arithmetic. `beat` is the music's beat, `None`
/// when no song plays (everything is put in its final place at once);
/// `may_rise` is "the first title of the run, not skipped". While b = beat x
/// 0.5 + 0.035 is below 20 the container rises in 20 steps, one per whole b,
/// each eased over its first fifth; after that the logo bobs 5 pixels down
/// from x = 0.1 to 0.5 of each bar (x = the fraction of b x 0.5), easing over
/// a tenth on each side.
pub fn rise(beat: Option<f64>, may_rise: bool) -> Rise {
    let Some(beat) = beat else {
        return Rise { rising: false, container_y: 0.0, logo_y: Some(LOGO_TOP) };
    };
    let b = beat * BEAT_SCALE + BEAT_SHIFT;
    if may_rise && b < RISE_STEPS {
        // `b % 1.0` is the C library's fmod, as the game calls it.
        let ease = smoothstep(0.0, RISE_EASE, b % 1.0);
        let p = f64::min(1.0, (b.floor() as i32 as f64 + ease) / RISE_STEPS);
        let distance = HEIGHT as f64 - LOGO_TOP;
        return Rise { rising: true, container_y: math_round((0.0 - distance) * p + distance) as f64, logo_y: None };
    }
    let x = (b * BEAT_SCALE) % 1.0;
    let bob = math_round((smoothstep(0.0, 0.1, x) - smoothstep(0.5, 0.6, x)) * BOB);
    Rise { rising: false, container_y: 0.0, logo_y: Some(bob as f64 + LOGO_TOP) }
}

/// The quads of the title screen at rest (milestone 1b's still), or what is
/// missing.
pub fn build(gallery: &Gallery) -> Result<Vec<Quad>, String> {
    Ok(TitleScreen::at_rest(gallery)?.quads(gallery))
}

/// Draws the title screen at rest into `screen` (cleared first).
pub fn draw(gallery: &Gallery, screen: &mut Screen) -> Result<(), String> {
    let quads = build(gallery)?;
    screen.clear();
    for q in &quads {
        screen.draw(q, &gallery.pictures);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_two_menu_buttons_sit_5_apart() {
        // 2 x 19 rows plus 10 between them is 48; the 10 left over is
        // shared out per button, 5 each; centred on 260 the column starts
        // at 236.
        assert_eq!(menu_column(&[19, 19], 260.0), [236, 260]);
    }

    #[test]
    fn the_title_rises_in_20_steps_over_23_6_s() {
        use crate::aud::MusicBeat;
        let at = |t: f64| rise(Some(MusicBeat::beat(t)), true);
        // At the start: b = 0.035, step 0 eased by smoothstep(0, 0.2, 0.035).
        let start = at(0.0);
        assert!(start.rising);
        let ease = smoothstep(0.0, 0.2, 0.035);
        assert_eq!(start.container_y, math_round(292.0 - 292.0 * ease / 20.0) as f64);
        // The steps settle on 292 x (1 - n / 20), rounded: 14.6 a step.
        assert_eq!(at(1.0).container_y, 277.0);
        // Rising until b reaches 20, at beat 39.93: just before 23.6 s.
        assert!(at(23.55).rising);
        let end = at(23.65);
        assert!(!end.rising);
        assert_eq!(end.container_y, 0.0);
        // Every frame of the rise only ever moves up.
        let mut last = f64::MAX;
        for frame in 0..(23.6 * 60.0) as i32 {
            let y = at(frame as f64 / 60.0).container_y;
            assert!(y <= last, "frame {frame}: {y} after {last}");
            last = y;
        }
    }

    #[test]
    fn skipped_or_not_first_means_no_rise_and_the_logo_bobs() {
        use crate::aud::MusicBeat;
        let r = rise(Some(MusicBeat::beat(1.0)), false);
        assert_eq!((r.rising, r.container_y), (false, 0.0));
        // b x 0.5 runs 0..1 over a bar (2.4 s at 100 bpm). At 0.6 s, b =
        // 0.535, x = 0.2675: fully down. At 1.8 s, x = 0.7675: back up.
        assert_eq!(rise(Some(MusicBeat::beat(0.6)), false).logo_y, Some(33.0));
        assert_eq!(rise(Some(MusicBeat::beat(1.8)), false).logo_y, Some(28.0));
        // No song: everything in place at once.
        assert_eq!(rise(None, true), Rise { rising: false, container_y: 0.0, logo_y: Some(28.0) });
    }

    #[test]
    fn a_tall_column_is_cut_to_the_screen() {
        // 20 buttons of 19 would need 380 + 190; the limit is 320 - 40.
        let tops = menu_column(&[19; 20], 160.0);
        assert_eq!(tops[0], 20);
        assert!(tops.windows(2).all(|p| p[1] - p[0] == 19 - 5));
    }
}
