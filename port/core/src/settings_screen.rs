//! The settings screen (`play.screen.SettingsScreen` with its list
//! `SettingsMenu`, rows `SettingRow` and sizes `SettingDim`; docs/screens.md
//! part 4), opened by the title's settings button. Desktop, English: the
//! rows Fullscreen, Nudity, Easy Mode, Date Format, Music and Sound, then
//! DONE (Escape presses it). scripts/reference/settingsscreen.py builds the
//! same quads; port/core/tests/settings_screen.rs compares the two.
//!
//! Left out: the Language row and the `web` and `twitter` buttons (the
//! user's decisions), the Vibration and Device rows and the version text
//! (not on desktop).
//!
//! A click only calls a setter of [`Settings`]; the rows show the settings
//! again whenever their change counter moves (`SettingsMenu.update`), and
//! `Game` applies and saves them.

use crate::aud::{AudioHost, Speaker};
use crate::button::{Background, Button, Look};
use crate::input::{Cursor, EntId, Input, Rect};
use crate::num::lerp_scale;
use crate::pages::{Builder, Gallery};
use crate::picture::Picture;
use crate::raster::Quad;
use crate::screen::{HEIGHT, WIDTH};
use crate::settings::{self, Settings, DATE_FORMATS};
use crate::text::Text;

/// The song this screen asks for.
pub const SONG: &str = "Theme";

/// The desktop layout's values (docs/screens.md part 4).
const HEADER_Y: f64 = 13.0;
const FOOTER_Y: f64 = 290.0;
const NOTCH_HEIGHT: i32 = 0;
const BUTTON_W: i32 = 15;
const BUTTON_H: i32 = 15;
const PADDING: i32 = 4;
const BUTTON_X: i32 = 180;
const ROW_H: i32 = PADDING + BUTTON_H;
const BAR_W: i32 = BUTTON_W * 50 / 15;
/// The easy tip sits this far right of the button column, for 3 seconds.
const TIP_DX: i32 = 30;
const TIP_TIME: f64 = 3.0;
/// The header title's padding left and right.
const HEADER_PAD: i32 = 8;
const PUSH_ROWS: i32 = 19;
const GREEN: u32 = 0x55_6855;
const WHITE: u32 = 0xFFFF_FFFF;
const BLACK: u32 = 0xFF00_0000;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Kind {
    Fullscreen,
    Nudity,
    EasyMode,
    DateFormat,
    Music,
    Sound,
}

/// A `SettingRow`, in the list's coordinates.
struct Row {
    kind: Kind,
    ent: EntId,
    label: String,
    label_width: f64,
    /// The row's top inside the list.
    y: f64,
    height: f64,
    /// Everything but the label sits this much lower when the label needs a
    /// line of its own (`splitOntoTwoLinesIfNecessary`; 0 in English).
    shift: f64,
    /// The tick box, or minus then plus.
    buttons: Vec<Button>,
    /// `volumePerc` of a volume row.
    volume: f64,
    /// The date row's example text and where it starts.
    text: String,
    text_x: f64,
}

impl Row {
    fn has_bar(&self) -> bool {
        matches!(self.kind, Kind::Music | Kind::Sound)
    }

    fn bar_x(&self) -> f64 {
        (BUTTON_X - PADDING - BAR_W) as f64
    }

    /// The level's rectangle in the row (also where the bar takes the
    /// pointer): 46 wide at most, 12 high.
    fn level_rect(&self, ascent: f64) -> Rect {
        [self.bar_x() + 2.0, 1.0 + self.shift, (BAR_W - 4) as f64, ascent - 4.0]
    }
}

/// `SettingRow.makeModeImages` for one column: a black box 15 x 15 (taller
/// if the icon needs it) with a dotted white border, the icon pasted in the
/// middle; the pressed picture has its inside filled white first.
fn mode_pictures(icon: &Picture, internal_padding: i32) -> (Picture, Picture) {
    let w = BUTTON_W as u32;
    let h = BUTTON_H.max(icon.height as i32 + 2 + internal_padding * 2) as u32;
    let white = [255, 255, 255, 255];
    let mut normal = Picture::filled(w, h, [0, 0, 0, 255]);
    for x in 0..w {
        if x % 2 == 0 {
            normal.set(x, 0, white);
        }
        if x & 1 == (h - 1) & 1 {
            normal.set(x, h - 1, white);
        }
    }
    for y in 0..h {
        if y % 2 == 0 {
            normal.set(0, y, white);
        }
        if (w - 1) & 1 == y & 1 {
            normal.set(w - 1, y, white);
        }
    }
    let mut pressed = normal.clone();
    pressed.fill_rect([2, 2, w as i32 - 4, h as i32 - 4], white);
    let centre = |p: &Picture| ((p.width as f64 - icon.width as f64) * 0.5, (p.height as f64 - icon.height as f64) * 0.5);
    let (x, y) = centre(&normal);
    normal.paste_blend(icon, x, y);
    let (x, y) = centre(&pressed);
    pressed.paste_blend(icon, x, y);
    (normal, pressed)
}

/// `updateDateFormatText`: the example of the chosen format, and where it
/// starts so that it ends before the buttons.
fn date_text(gallery: &Gallery, settings: &Settings) -> (String, f64) {
    let font = gallery.font("title_tall").unwrap();
    let index = settings.date_format_index().clamp(0, DATE_FORMATS.len() as i32 - 1) as usize;
    let text = DATE_FORMATS[index].2;
    let width = Text::new(text).build(font).width as f64;
    (text.to_string(), (BUTTON_X - PADDING) as f64 - width)
}

/// The normal and pressed pictures made from an icon, kept in the gallery.
fn mode_look(gallery: &mut Gallery, look: &str, icon_file: &str, internal_padding: i32) -> Result<Look, String> {
    let mut index = |pressed: bool| {
        let name = format!("{icon_file}{}", if pressed { ":pressed" } else { "" });
        gallery.made_picture(&name, |g| {
            let icon = g.picture(icon_file).ok_or_else(|| format!("{icon_file} is missing from the pack"))?;
            let (n, p) = mode_pictures(&g.pictures[icon], internal_padding);
            Ok(if pressed { p } else { n })
        })
    };
    let (normal, pressed) = (index(false)?, index(true)?);
    let piece = |image: usize, g: &Gallery| {
        let p = &g.pictures[image];
        Background::Piece { image, src: [0, 0, p.width as i32, p.height as i32] }
    };
    Ok(Look::new(look, piece(normal, gallery), piece(pressed, gallery)))
}

pub struct SettingsScreen {
    header: usize,
    header_text: String,
    header_text_x: f64,
    header_text_y: f64,
    rows: Vec<Row>,
    /// The list's top left corner.
    list_x: f64,
    list_y: f64,
    done: Button,
    tip: String,
    tip_visible: bool,
    tip_hide_time: f64,
    ascent: f64,
    label_y: f64,
    /// The settings' change counter when the rows last showed them.
    seen_generation: u32,
}

impl SettingsScreen {
    /// The constructor (`SettingsScreen`, `SettingsMenu` in its `Title`
    /// form). Asking for the song is the screen change's job; see [`SONG`].
    pub fn new(gallery: &mut Gallery, settings: &Settings) -> Result<SettingsScreen, String> {
        let string = |g: &Gallery, id: &str| g.strings.get(id).cloned().ok_or_else(|| format!("text {id} is missing from the pack"));
        for font in ["title_tall", "ui_large"] {
            gallery.font(font).ok_or_else(|| format!("font {font} is missing"))?;
        }
        let header = gallery.picture("ScreenHeader.png").ok_or("ScreenHeader.png is missing from the pack")?;
        let push = gallery.picture("PushButton.png").ok_or("PushButton.png is missing from the pack")?;
        let font = gallery.font("title_tall").unwrap();
        let (ascent, label_y) = (font.ascent as f64, (font.cap_height - font.ascent) as f64);
        let width_of = |g: &Gallery, s: &str| Text::new(s).build(g.font("title_tall").unwrap()).width as f64;
        let w = WIDTH as f64;

        // The header (GameScreen.addHeader): the picture, then the title
        // with its middle on the picture's bottom edge.
        let header_text = string(gallery, "menu_settings")?;
        let mut t = Text::new(&header_text);
        t.padding_x = HEADER_PAD;
        let built = t.build(font);
        let header_h = gallery.pictures[header].height as f64;
        let header_text_x = (w * 0.5 - built.width as f64 * 0.5).floor();
        let header_text_y = ((header_h + HEADER_Y) - built.height as f64 * 0.5).floor() + 0.0;
        let header_bottom = header_text_y + built.height as f64;

        // The rows, each with its buttons; the button pictures are made
        // once and kept (SettingDim).
        let button_y = (ascent * 0.5 - BUTTON_H as f64 * 0.5).floor() - 1.0;
        let on = mode_look(gallery, "on", "SettingButtonOn.png", 0)?;
        let off = mode_look(gallery, "off", "SettingButtonOff.png", 2)?;
        let plus = mode_look(gallery, "normal", "SettingButtonPlus.png", 2)?;
        let minus = mode_look(gallery, "normal", "SettingButtonMinus.png", 2)?;
        let mut next_ent: EntId = 1;
        let mut ent = || {
            next_ent += 1;
            next_ent
        };
        let mut rows = Vec::new();
        for (id, kind) in [
            ("menu_fullscreen", Kind::Fullscreen),
            ("menu_nudity", Kind::Nudity),
            ("menu_easy", Kind::EasyMode),
            ("menu_dateformat", Kind::DateFormat),
            ("menu_music", Kind::Music),
            ("menu_sound", Kind::Sound),
        ] {
            let label = string(gallery, id)?;
            let mut buttons = Vec::new();
            match kind {
                Kind::Fullscreen | Kind::Nudity | Kind::EasyMode => {
                    let mut b = Button::new("checkbox", ent(), "", off.clone());
                    b.looks.push(on.clone());
                    (b.x, b.y) = (BUTTON_X as f64, button_y);
                    buttons.push(b);
                }
                Kind::DateFormat | Kind::Music | Kind::Sound => {
                    let mut m = Button::new("MINUS", ent(), "", minus.clone());
                    (m.x, m.y) = (BUTTON_X as f64, button_y);
                    let mut p = Button::new("PLUS", ent(), "", plus.clone());
                    (p.x, p.y) = (BUTTON_X as f64 + m.size().0 as f64 + PADDING as f64, button_y);
                    buttons.extend([m, p]);
                }
            }
            let (text, text_x) = if kind == Kind::DateFormat { date_text(gallery, settings) } else { (String::new(), 0.0) };
            rows.push(Row {
                kind,
                ent: ent(),
                label_width: width_of(gallery, &label),
                label,
                y: 0.0,
                height: ROW_H as f64,
                shift: 0.0,
                buttons,
                volume: 0.0,
                text,
                text_x,
            });
        }

        // Stacking (the end of the SettingsMenu constructor): each row
        // splits if it must, the list is as wide as its widest row.
        let mut total_w: f64 = 0.0;
        let mut y = 0.0;
        for row in &mut rows {
            let mut left = f64::INFINITY;
            if row.has_bar() {
                left = left.min(row.bar_x());
            }
            if row.kind == Kind::DateFormat {
                left = left.min(row.text_x);
            }
            for b in &row.buttons {
                left = left.min(b.x);
            }
            if row.label_width + 0.0 >= left - PADDING as f64 {
                row.shift = ROW_H as f64;
                for b in &mut row.buttons {
                    b.y += ROW_H as f64;
                }
                row.height += ROW_H as f64;
            }
            let mut right = row.label_width;
            if row.has_bar() {
                right = right.max(row.bar_x() + BAR_W as f64);
            }
            if row.kind == Kind::DateFormat {
                right = right.max(row.text_x + width_of(gallery, &row.text));
            }
            for b in &row.buttons {
                right = right.max(b.x + b.size().0 as f64);
            }
            total_w = total_w.max(right);
            row.y = y;
            y += row.height;
        }
        let total_h = y - PADDING as f64;

        // DONE (Menu.addPushButton: centred, its column centred on 290),
        // and the list centred between the header and DONE.
        let push_w = gallery.pictures[push].width as i32;
        let look = Look::new(
            "normal",
            Background::Piece { image: push, src: [0, 0, push_w, PUSH_ROWS] },
            Background::Piece { image: push, src: [0, PUSH_ROWS, push_w, PUSH_ROWS] },
        )
        .with_text(&string(gallery, "menu_done")?, GREEN, 0);
        let mut done = Button::new("back", 1, "ui_large", look);
        done.set_as_back_button();
        // Menu.applyCenterY with one button: no gaps to share out.
        let column = f64::min((HEIGHT as i32 - NOTCH_HEIGHT - 40) as f64, PUSH_ROWS as f64);
        done.x = (w * 0.5 - push_w as f64 * 0.5).floor();
        done.y = (FOOTER_Y - column * 0.5) as i32 as f64;
        Ok(SettingsScreen {
            header,
            header_text,
            header_text_x,
            header_text_y,
            rows,
            list_x: (w * 0.5 - total_w * 0.5).floor(),
            list_y: ((done.y - header_bottom) * 0.5 + header_bottom - total_h * 0.5).floor(),
            done,
            tip: string(gallery, "menu_easytip")?,
            tip_visible: false,
            tip_hide_time: -100.0,
            ascent,
            label_y,
            seen_generation: 0,
        })
    }

    /// `updateDateFormatText` on the date row.
    fn show_date_format(&mut self, gallery: &Gallery, settings: &Settings) {
        if let Some(row) = self.rows.iter_mut().find(|r| r.kind == Kind::DateFormat) {
            (row.text, row.text_x) = date_text(gallery, settings);
        }
    }

    /// Shows the easy tip for 3 seconds from the clock's `time`.
    pub fn show_easy_tip(&mut self, time: f64) {
        self.tip_visible = true;
        self.tip_hide_time = time + TIP_TIME;
    }

    /// `SettingsMenu.update`, every frame: the rows follow the settings when
    /// their counter has moved; the tip hides once its time is up.
    pub fn update(&mut self, gallery: &Gallery, settings: &Settings, time: f64) {
        if self.seen_generation != settings.generation() {
            self.seen_generation = settings.generation();
            for row in &mut self.rows {
                let on = match row.kind {
                    Kind::Music => {
                        row.volume = settings.music_volume();
                        continue;
                    }
                    Kind::Sound => {
                        row.volume = settings.sound_volume();
                        continue;
                    }
                    Kind::DateFormat => continue,
                    Kind::Fullscreen => settings.fullscreen(),
                    Kind::Nudity => settings.nudity(),
                    Kind::EasyMode => settings.easy_mode(),
                };
                row.buttons[0].set_look(if on { "on" } else { "off" });
            }
            self.show_date_format(gallery, settings);
        }
        self.tip_visible = time < self.tip_hide_time;
    }

    /// The screen's input: DONE first, then the rows from the last up (each
    /// row's buttons, then its bar). A click calls its setter; `time` is the
    /// game's clock, for the easy tip. Returns the id of a clicked menu
    /// button (`back`).
    pub fn react(&mut self, input: &mut Input, speaker: &mut Speaker, host: &mut dyn AudioHost, settings: &mut Settings, time: f64) -> Option<String> {
        let mut clicked = None;
        if self.done.react((0.0, 0.0), input, speaker, host) {
            clicked = Some(self.done.id.clone());
        }
        let ascent = self.ascent;
        for row in self.rows.iter_mut().rev() {
            let origin = (self.list_x, self.list_y + row.y);
            for i in (0..row.buttons.len()).rev() {
                if !row.buttons[i].react(origin, input, speaker, host) {
                    continue;
                }
                let up = row.buttons[i].id == "PLUS";
                match row.kind {
                    Kind::Fullscreen => settings.set_fullscreen(!settings.fullscreen()),
                    Kind::Nudity => settings.set_nudity(!settings.nudity()),
                    Kind::EasyMode => {
                        settings.set_easy_mode(!settings.easy_mode());
                        if settings.easy_mode() {
                            self.tip_visible = true;
                            self.tip_hide_time = time + TIP_TIME;
                        } else {
                            self.tip_visible = false;
                            self.tip_hide_time = -100.0;
                        }
                    }
                    Kind::DateFormat => {
                        let (i, last) = (settings.date_format_index(), DATE_FORMATS.len() as i32 - 1);
                        settings.set_date_format_index(if up { if last <= i { last } else { i + 1 } } else { (i - 1).max(0) });
                    }
                    Kind::Music => settings.set_music_volume(settings::volume_step(settings.music_volume(), up)),
                    Kind::Sound => settings.set_sound_volume(settings::volume_step(settings.sound_volume(), up)),
                }
            }
            // The bar (SettingRow.react): held down on it, the volume is the
            // pointer's place along it.
            if row.has_bar() {
                let r = row.level_rect(ascent);
                let rect: Rect = [origin.0 + r[0], origin.1 + r[1], r[2], r[3]];
                if let Some(p) = input.pointer_over(row.ent, &rect) {
                    p.set_cursor(Cursor::Hand);
                    if p.down {
                        p.capture(row.ent);
                        let v = settings::volume_from_bar(lerp_scale(p.pos.0, rect[0], rect[0] + rect[2], 0.0, 1.0));
                        match row.kind {
                            Kind::Music => settings.set_music_volume(v),
                            _ => settings.set_sound_volume(v),
                        }
                    }
                }
            }
        }
        clicked
    }

    /// The quads, in drawing order: the header, the rows (each its label,
    /// bar, text and tip, then its buttons), DONE.
    pub fn quads(&self, gallery: &Gallery) -> Vec<Quad> {
        let mut b = Builder { gallery, quads: Vec::new() };
        let font = gallery.font("title_tall").unwrap();
        let pic = &gallery.pictures[self.header];
        let (hw, hh) = (pic.width as i32, pic.height as i32);
        b.part(self.header, (WIDTH as f64 * 0.5 - hw as f64 * 0.5).floor(), HEADER_Y, [0, 0, hw, hh]);
        b.text(font, &self.header_text, self.header_text_x, self.header_text_y, |t| {
            t.background = BLACK;
            t.padding_x = HEADER_PAD;
        });
        for row in &self.rows {
            let (x, y) = (self.list_x, self.list_y + row.y);
            b.text(font, &row.label, x, y + self.label_y, |_| {});
            let dy = row.shift;
            if row.has_bar() {
                let bx = x + row.bar_x();
                b.fill(bx, y - 1.0 + dy, BAR_W as f64, self.ascent, WHITE);
                b.fill(bx + 1.0, y + dy, BAR_W as f64 - 2.0, self.ascent - 2.0, BLACK);
                let level = (BAR_W - 4) as f64 * row.volume;
                if level >= 1.0 {
                    b.fill(bx + 2.0, y + 1.0 + dy, level, self.ascent - 4.0, WHITE);
                }
            }
            if row.kind == Kind::DateFormat {
                b.text(font, &row.text, x + row.text_x, y + self.label_y + dy, |_| {});
            }
            if row.kind == Kind::EasyMode && self.tip_visible {
                b.text(font, &self.tip, x + (BUTTON_X + TIP_DX) as f64, y + self.label_y + dy, |_| {});
            }
            for button in &row.buttons {
                button.draw(&mut b, gallery, (x, y));
            }
        }
        self.done.draw(&mut b, gallery, (0.0, 0.0));
        b.quads
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn icon(w: u32, h: u32) -> Picture {
        Picture::filled(w, h, [0, 0, 0, 0])
    }

    #[test]
    fn a_button_picture_is_a_dotted_box_15_square() {
        let (normal, pressed) = mode_pictures(&icon(5, 5), 2);
        assert_eq!((normal.width, normal.height), (15, 15));
        for (x, y) in [(0, 0), (2, 0), (14, 0), (0, 14), (14, 14), (0, 2), (14, 2)] {
            assert_eq!(normal.texel(x, y), [255; 4], "a dot at {x}, {y}");
        }
        for (x, y) in [(1, 0), (0, 1), (13, 14), (14, 13), (7, 7)] {
            assert_eq!(normal.texel(x, y), [0, 0, 0, 255], "black at {x}, {y}");
        }
        // Pressed: the inside, 2 pixels in, is white; the gap stays black.
        assert_eq!(pressed.texel(2, 2), [255; 4]);
        assert_eq!(pressed.texel(12, 12), [255; 4]);
        assert_eq!(pressed.texel(1, 1), [0, 0, 0, 255]);
        assert_eq!(pressed.texel(13, 13), [0, 0, 0, 255]);
    }

    #[test]
    fn a_tall_icon_makes_a_taller_button() {
        let (normal, _) = mode_pictures(&icon(9, 13), 2);
        assert_eq!((normal.width, normal.height), (15, 19));
    }
}
