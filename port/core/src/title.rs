//! The title screen as a still (milestone 1b, docs/milestone-1.md): where it
//! rests once the title has risen, with no button pressed and no music
//! (so the logo does not bob). Positions from docs/screens.md part 2 and
//! docs/buttons.md; scripts/reference/titlescreen.py builds the same quads.
//!
//! Left out: the quit button (the user's decision) and the version button
//! (its text is not read yet).

use crate::font::Font;
use crate::pages::{Builder, Gallery};
use crate::raster::{Quad, Screen};
use crate::screen::{HEIGHT, WIDTH};
use crate::text::{Align, Text};

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
/// The credit's run-time picture: black, 140 x 12.
const CREDIT_SIZE: (i32, i32) = (140, 12);
/// A button text's colour (0x556855), opaque as `Button.applyMode` makes it.
const GREEN: u32 = 0xFF55_6855;

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

/// A button's text, centred on a `w` x `h` button whose corner is (x, y).
fn button_text(b: &mut Builder, font: &Font, string: &str, x: f64, y: f64, w: i32, h: i32) {
    let mut t = Text::new(string);
    t.align = Align::Center;
    t.color = GREEN;
    let built = t.build(font);
    let tx = x + centred(w as f64, built.width as f64);
    let ty = y + centred(h as f64, built.height as f64);
    b.text(font, string, tx, ty, |t| {
        t.align = Align::Center;
        t.color = GREEN;
    });
}

/// The quads of the title screen, in drawing order, or what is missing.
pub fn build(gallery: &Gallery) -> Result<Vec<Quad>, String> {
    let picture = |file: &str| gallery.picture(file).ok_or_else(|| format!("{file} is missing from the pack"));
    let string = |id: &str| gallery.strings.get(id).ok_or_else(|| format!("text {id} is missing from the pack"));
    let font = |id: &str| gallery.font(id).ok_or_else(|| format!("font {id} is missing"));
    let (logo, push, settings) = (picture("Title.png")?, picture("PushButton.png")?, picture("SettingsButton.png")?);
    let (ui_large, regular) = (font("ui_large")?, font("regular")?);
    let (w, h) = (WIDTH as f64, HEIGHT as f64);

    let mut b = Builder { gallery, quads: Vec::new() };
    b.fill(0.0, 0.0, w, h, 0xFF00_0000);

    let logo_pic = &gallery.pictures[logo];
    b.part(logo, centred(w, logo_pic.width as f64), LOGO_TOP, [0, 0, logo_pic.width as i32, logo_pic.height as i32]);

    let push_w = gallery.pictures[push].width as i32;
    let x = centred(w, push_w as f64);
    let labels = [string("menu_story")?, string("menu_endless")?];
    for (label, top) in labels.iter().zip(menu_column(&[PUSH_ROWS; 2], MENU_CENTER_Y)) {
        let y = top as f64;
        b.part(push, x, y, [0, 0, push_w, PUSH_ROWS]);
        button_text(&mut b, ui_large, label, x, y, push_w, PUSH_ROWS);
    }

    let settings_w = gallery.pictures[settings].width as i32;
    b.part(settings, EDGE, h - EDGE - SETTINGS_ROWS as f64, [0, 0, settings_w, SETTINGS_ROWS]);

    let (cw, ch) = CREDIT_SIZE;
    let (cx, cy) = (centred(w, cw as f64), h - ch as f64 - EDGE);
    b.fill(cx, cy, cw as f64, ch as f64, 0xFF00_0000);
    button_text(&mut b, regular, string("created_by")?, cx, cy, cw, ch);
    Ok(b.quads)
}

/// Draws the title screen into `screen` (cleared first).
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
    fn a_tall_column_is_cut_to_the_screen() {
        // 20 buttons of 19 would need 380 + 190; the limit is 320 - 40.
        let tops = menu_column(&[19; 20], 160.0);
        assert_eq!(tops[0], 20);
        assert!(tops.windows(2).all(|p| p[1] - p[0] == 19 - 5));
    }
}
