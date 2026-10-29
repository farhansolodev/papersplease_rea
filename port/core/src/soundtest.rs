//! The sound test page of milestone 2 (`?page=sounds`): the port's own test
//! material, not a game screen. Every effect and song in a grid of four
//! columns, the chosen one boxed, playing ones green, and a few lines of
//! state under it. The host does the keys and the sound player.

use crate::pages::{Builder, Gallery};
use crate::raster::Screen;
use crate::screen::{HEIGHT, WIDTH};

/// Rows per column: four columns of 28 hold all 111 sounds.
pub const ROWS: usize = 28;
pub const COLUMNS: usize = 4;
const TOP: f64 = 22.0;
const COLUMN_WIDTH: f64 = 142.0;
const LINE: f64 = 9.0;

pub struct Entry {
    pub name: String,
    pub playing: bool,
}

/// Moves the choice by a key: `dx` columns and `dy` rows, wrapping inside
/// the list (the last column may be shorter).
pub fn moved(selected: usize, count: usize, dx: i32, dy: i32) -> usize {
    if count == 0 {
        return 0;
    }
    let step = dx as i64 * ROWS as i64 + dy as i64;
    (selected as i64 + step).rem_euclid(count as i64) as usize
}

/// Draws the page into `screen` (cleared first).
pub fn draw(gallery: &Gallery, entries: &[Entry], selected: usize, lines: &[String], screen: &mut Screen) {
    let font = gallery.font("regular").expect("font `regular`");
    let mut b = Builder { gallery, quads: Vec::new() };
    b.fill(0.0, 0.0, WIDTH as f64, HEIGHT as f64, 0xFF202830);
    b.text(font, "Sound test: arrows choose, Enter plays once, L plays looping, S stops all,", 4.0, 2.0, |_| {});
    b.text(font, "Space pauses or resumes the effects, 1 / 2 effects volume down / up, 3 / 4 music.", 4.0, 11.0, |_| {});
    for (i, e) in entries.iter().enumerate() {
        let x = 4.0 + (i / ROWS) as f64 * COLUMN_WIDTH;
        let y = TOP + (i % ROWS) as f64 * LINE;
        let color = if e.playing { 0xFF80FF80 } else { 0xFFC8C8C8 };
        b.text(font, &e.name, x, y, |t| {
            t.color = color;
            if i == selected {
                t.background = 0xFF3355AA;
            }
        });
    }
    let mut y = TOP + ROWS as f64 * LINE + 4.0;
    for line in lines {
        b.text(font, line, 4.0, y, |t| t.color = 0xFFFFCC33);
        y += LINE;
    }
    screen.clear();
    for q in &b.quads {
        screen.draw(q, &gallery.pictures);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn the_choice_moves_and_wraps() {
        assert_eq!(moved(0, 111, 0, 1), 1);
        assert_eq!(moved(0, 111, 0, -1), 110);
        assert_eq!(moved(0, 111, 1, 0), 28);
        assert_eq!(moved(100, 111, 1, 0), 17);
        assert_eq!(moved(5, 111, -1, 0), 88);
        assert_eq!(moved(0, 0, 1, 1), 0);
    }
}
