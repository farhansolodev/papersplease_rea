//! The pause screen (`play.screen.PauseScreen`) and the confirm box it
//! opens (`play.screen.Confirm`), as milestone 4b builds them
//! (docs/screens.md parts 3 and 4, docs/milestone-4.md "4b").
//! scripts/reference/pausescreen.py draws the same pictures;
//! port/core/tests/pause.rs compares the two.
//!
//! Desktop, English: the header "PAUSED", RESUME and MAIN MENU centred on
//! y 270 (QUIT is left out, the user's decision), the settings list in its
//! `Pause` form between them. RESUME is the back button (Escape presses it
//! on release). MAIN MENU opens the confirm box: a half-black cover over
//! the whole screen, the frame `ConfirmBox.png` and two buttons, a red MAIN
//! MENU (which freezes the box and goes to the title) and CANCEL (Escape
//! presses it; it hides the box).

use crate::aud::{AudioHost, Speaker};
use crate::button::Button;
use crate::input::{EntId, Input};
use crate::pages::{Builder, Gallery};
use crate::raster::Screen;
use crate::screen::{HEIGHT, WIDTH};
use crate::settings::Settings;
use crate::settings_screen::{place_menu, push_button, Header, Purpose, SettingsMenu};

/// The pause screen's menu is centred on `kPixelHeight x 270 / 320`.
const MENU_CENTER_Y: f64 = (HEIGHT as i32 * 270 / 320) as f64;
/// `Confirm`'s statics: the gap between buttons and a button's height.
const CONFIRM_GAP: f64 = 10.0;
const CONFIRM_BUTTON_H: f64 = 19.0;
/// The layout's `confirmBoxPadding` (desktop).
const CONFIRM_PADDING: (f64, f64) = (15.0, 20.0);
/// `ConfirmBox.png`'s nine-slice centre: 10 pixels in on every side.
const FRAME_BORDER: i32 = 10;
/// The confirm box's back fill: black at alpha 0.5.
const COVER_ALPHA: f32 = 0.5;

/// What a click on the pause screen asks of the game.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PauseAction {
    /// `GameTransition.setPause(false)`.
    Resume,
    /// `GameTransition.fadeToMainMenu()`.
    MainMenu,
}

/// One option of a confirm box: its id, the text id of its button, red,
/// frozen after a click, Escape presses it.
pub struct ConfirmOption {
    pub id: &'static str,
    pub text_id: &'static str,
    pub dangerous: bool,
    pub freeze_after_click: bool,
    pub back_button: bool,
}

/// `play.screen.Confirm`: hidden until shown.
pub struct Confirm {
    /// Switch 1: drawn, updated, takes input.
    active: bool,
    /// Switch 4: takes input (cleared by a click on a freezing option).
    input: bool,
    frame_picture: usize,
    /// The frame's outer rectangle.
    frame: [f64; 4],
    buttons: Vec<Button>,
}

impl Confirm {
    /// The constructor (`Confirm`, hidden) and `show` with an empty message.
    pub fn show(gallery: &Gallery, options: &[ConfirmOption], first_ent: EntId) -> Result<Confirm, String> {
        let frame_picture = gallery.picture("ConfirmBox.png").ok_or("ConfirmBox.png is missing from the pack")?;
        let dw = {
            let p = &gallery.pictures[frame_picture];
            p.width as f64
        };
        let (w, h) = (WIDTH as f64, HEIGHT as f64);
        // The constructor: the frame at its picture's size, centred.
        let x = (w * 0.5 - dw * 0.5).floor() as i32 as f64;
        // show: with no message the gap between buttons is doubled and the
        // box is the buttons and twice the padding high, centred up and down.
        let gap = CONFIRM_GAP + CONFIRM_GAP;
        let n = options.len() as f64;
        let buttons_h = n * CONFIRM_BUTTON_H + (n - 1.0) * gap;
        let height = buttons_h + (CONFIRM_PADDING.1 + CONFIRM_PADDING.1);
        let y = (h * 0.5 - height * 0.5).floor() as i32 as f64;
        let frame = [x, y, dw, height];
        let mut by = ((height + y) - buttons_h) - CONFIRM_PADDING.1;
        let mut buttons = Vec::new();
        for (i, o) in options.iter().enumerate() {
            let mut b = push_button(gallery, o.id, first_ent + i as EntId, o.text_id, o.dangerous)?;
            b.x = (dw * 0.5 - b.size().0 as f64 * 0.5).floor() as i32 as f64 + x;
            b.y = by;
            by = by + gap + CONFIRM_BUTTON_H;
            if o.id == "back" || o.id == "cancel" || o.back_button {
                b.set_as_back_button();
            }
            buttons.push(b);
        }
        Ok(Confirm { active: true, input: true, frame_picture, frame, buttons })
    }

    /// The box's input: its buttons from the last to the first, then the
    /// box masks the whole screen for the rest of the frame. A click hides
    /// the box, or freezes it for an option that says so, and returns the
    /// option's id.
    fn react(&mut self, options: &[ConfirmOption], input: &mut Input, speaker: &mut Speaker, host: &mut dyn AudioHost) -> Option<&'static str> {
        if !self.active || !self.input {
            return None;
        }
        let mut clicked = None;
        for i in (0..self.buttons.len()).rev() {
            if self.buttons[i].react((0.0, 0.0), input, speaker, host) {
                let o = &options[i];
                if o.freeze_after_click {
                    self.input = false;
                } else {
                    self.active = false;
                }
                clicked = Some(o.id);
            }
        }
        if self.active && self.input {
            input.mask_area([0.0, 0.0, WIDTH as f64, HEIGHT as f64]);
        }
        clicked
    }

    /// The box's frame and buttons (the cover under them is drawn by
    /// [`PauseScreen::draw`]).
    fn draw(&self, b: &mut Builder, gallery: &Gallery) {
        let p = &gallery.pictures[self.frame_picture];
        let (iw, ih) = (p.width as i32, p.height as i32);
        let [fx, fy, fw, fh] = self.frame;
        for (src, dst) in nine_slice((iw, ih), [FRAME_BORDER, FRAME_BORDER, iw - 2 * FRAME_BORDER, ih - 2 * FRAME_BORDER], (fw, fh)) {
            b.stretched(self.frame_picture, fx + dst[0], fy + dst[1], dst[2], dst[3], src);
        }
        for button in &self.buttons {
            button.draw(b, gallery, (0.0, 0.0));
        }
    }
}

/// `Frame.buildTiles`: nine (source, target) rectangles, the target in the
/// frame's own coordinates. The corners keep their size, the edges stretch
/// one way and the middle both ways.
pub(crate) fn nine_slice(image: (i32, i32), scale9: [i32; 4], outer: (f64, f64)) -> Vec<([i32; 4], [f64; 4])> {
    let (iw, ih) = image;
    let [sx, sy, sw, sh] = scale9;
    let xs = [0, sx, sx + sw, iw];
    let ys = [0, sy, sy + sh, ih];
    let right = outer.0 - (iw - (sx + sw)) as f64;
    let bottom = outer.1 - (ih - (sy + sh)) as f64;
    let xd = [0.0, sx as f64, right, outer.0];
    let yd = [0.0, sy as f64, bottom, outer.1];
    let mut tiles = Vec::new();
    for row in 0..3 {
        for col in 0..3 {
            let src = [xs[col], ys[row], xs[col + 1] - xs[col], ys[row + 1] - ys[row]];
            let dst = [xd[col], yd[row], xd[col + 1] - xd[col], yd[row + 1] - yd[row]];
            tiles.push((src, dst));
        }
    }
    tiles
}

const MAIN_MENU_OPTIONS: [ConfirmOption; 2] = [
    ConfirmOption { id: "confirm-mainmenu", text_id: "menu_mainmenu", dangerous: true, freeze_after_click: true, back_button: false },
    ConfirmOption { id: "confirm-cancel", text_id: "confirm_cancel", dangerous: false, freeze_after_click: false, back_button: true },
];

pub struct PauseScreen {
    header: Header,
    resume: Button,
    main_menu: Button,
    settings: SettingsMenu,
    confirm: Option<Confirm>,
}

impl PauseScreen {
    /// The constructor (desktop, without QUIT): the header, the menu, the
    /// settings list in its `Pause` form.
    pub fn new(gallery: &mut Gallery, settings: &Settings) -> Result<PauseScreen, String> {
        let header = Header::new(gallery, "menu_paused")?;
        let mut resume = push_button(gallery, "resume", 1, "menu_resume", false)?;
        let mut main_menu = push_button(gallery, "mainmenu", 2, "menu_mainmenu", false)?;
        place_menu(&mut [&mut resume, &mut main_menu], MENU_CENTER_Y);
        resume.set_as_back_button();
        let mut menu = SettingsMenu::new(gallery, settings, Purpose::Pause, 10)?;
        menu.centre_between(header.bottom, resume.y);
        Ok(PauseScreen { header, resume, main_menu, settings: menu, confirm: None })
    }

    /// Whether the confirm box shows.
    pub fn confirm_shown(&self) -> bool {
        self.confirm.as_ref().is_some_and(|c| c.active)
    }

    /// Every frame: the settings list follows the settings.
    pub fn update(&mut self, gallery: &Gallery, settings: &Settings, time: f64) {
        self.settings.update(gallery, settings, time);
    }

    /// The screen's input, newest parts first: the confirm box, the
    /// settings list, MAIN MENU, RESUME (`PauseScreen.menu_onClick` for the
    /// clicks).
    pub fn react(
        &mut self,
        gallery: &Gallery,
        input: &mut Input,
        speaker: &mut Speaker,
        host: &mut dyn AudioHost,
        settings: &mut Settings,
        time: f64,
    ) -> Result<Option<PauseAction>, String> {
        let mut action = None;
        if let Some(c) = &mut self.confirm {
            match c.react(&MAIN_MENU_OPTIONS, input, speaker, host) {
                Some("confirm-mainmenu") => action = Some(PauseAction::MainMenu),
                // `confirm-cancel` forgets the box; the next one is new.
                Some(_) => self.confirm = None,
                None => {}
            }
        }
        self.settings.react(input, speaker, host, settings, time);
        if self.main_menu.react((0.0, 0.0), input, speaker, host) {
            // showConfirm("confirm-mainmenu", MAIN MENU's text).
            if self.confirm.is_none() {
                self.confirm = Some(Confirm::show(gallery, &MAIN_MENU_OPTIONS, 30)?);
            }
        }
        if self.resume.react((0.0, 0.0), input, speaker, host) {
            action = Some(PauseAction::Resume);
        }
        Ok(action)
    }

    /// Draws the screen into `out` (over what is there): the header, the
    /// menu, the settings list; then, if shown, the confirm box's cover,
    /// frame and buttons.
    pub fn draw(&self, gallery: &Gallery, out: &mut Screen) {
        let mut b = Builder { gallery, quads: Vec::new() };
        self.header.draw(&mut b, gallery);
        self.resume.draw(&mut b, gallery, (0.0, 0.0));
        self.main_menu.draw(&mut b, gallery, (0.0, 0.0));
        self.settings.draw(&mut b, gallery);
        for q in &b.quads {
            out.draw(q, &gallery.pictures);
        }
        if let Some(c) = self.confirm.as_ref().filter(|c| c.active) {
            out.cover(COVER_ALPHA, &gallery.pictures);
            let mut b = Builder { gallery, quads: Vec::new() };
            c.draw(&mut b, gallery);
            for q in &b.quads {
                out.draw(q, &gallery.pictures);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_confirm_frame_stretches_only_its_middle_row() {
        let tiles = nine_slice((244, 192), [10, 10, 224, 172], (244.0, 98.0));
        assert_eq!(tiles.len(), 9);
        assert_eq!(tiles[0], ([0, 0, 10, 10], [0.0, 0.0, 10.0, 10.0]));
        assert_eq!(tiles[4], ([10, 10, 224, 172], [10.0, 10.0, 224.0, 78.0]));
        assert_eq!(tiles[8], ([234, 182, 10, 10], [234.0, 88.0, 10.0, 10.0]));
    }

    #[test]
    fn the_menu_centre_is_270() {
        assert_eq!(MENU_CENTER_Y, 270.0);
    }
}
