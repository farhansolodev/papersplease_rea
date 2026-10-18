//! Milestone 0's test card: a picture that shows by eye whether the screen
//! is the right size, drawn at a whole-number zoom, not blurred, not
//! colour-shifted, and stepping at 60 a second. It is the port's own
//! drawing, with a digit font of its own (3 x 5 blocks); nothing of the
//! game. Later milestones replace it with the game's quads.

use crate::screen::{HEIGHT, WIDTH};

/// Bytes in the picture: 4 per pixel (red, green, blue, alpha), rows top
/// to bottom.
pub const BYTES: usize = (WIDTH * HEIGHT * 4) as usize;

type Rgb = [u8; 3];
const WHITE: Rgb = [255, 255, 255];
const BLACK: Rgb = [0, 0, 0];
const YELLOW: Rgb = [255, 200, 0];

/// Digit shapes, 3 columns by 5 rows, one `u8` of 3 bits per row.
const DIGITS: [[u8; 5]; 10] = [
    [0b111, 0b101, 0b101, 0b101, 0b111],
    [0b010, 0b110, 0b010, 0b010, 0b111],
    [0b111, 0b001, 0b111, 0b100, 0b111],
    [0b111, 0b001, 0b111, 0b001, 0b111],
    [0b101, 0b101, 0b111, 0b001, 0b001],
    [0b111, 0b100, 0b111, 0b001, 0b111],
    [0b111, 0b100, 0b111, 0b101, 0b111],
    [0b111, 0b001, 0b010, 0b010, 0b010],
    [0b111, 0b101, 0b111, 0b101, 0b111],
    [0b111, 0b101, 0b111, 0b001, 0b111],
];

/// Left edge and width of the bouncing square's track.
const TRACK_LEFT: u32 = 20;
const TRACK_RIGHT: u32 = WIDTH - 20;
const SQUARE: u32 = 16;
const SQUARE_TOP: u32 = 240;

struct Canvas<'a> {
    pixels: &'a mut [u8],
}

impl Canvas<'_> {
    fn put(&mut self, x: u32, y: u32, c: Rgb) {
        if x < WIDTH && y < HEIGHT {
            let i = ((y * WIDTH + x) * 4) as usize;
            self.pixels[i..i + 4].copy_from_slice(&[c[0], c[1], c[2], 255]);
        }
    }

    fn rect(&mut self, x: u32, y: u32, w: u32, h: u32, c: Rgb) {
        for yy in y..y + h {
            for xx in x..x + w {
                self.put(xx, yy, c);
            }
        }
    }

    /// A number in the 3 x 5 font, each block `scale` pixels square, one
    /// block of gap between digits. Returns the width drawn.
    fn number(&mut self, mut n: u64, x: u32, y: u32, scale: u32, c: Rgb) -> u32 {
        let mut digits = Vec::new();
        loop {
            digits.push((n % 10) as usize);
            n /= 10;
            if n == 0 {
                break;
            }
        }
        digits.reverse();
        for (k, &d) in digits.iter().enumerate() {
            let dx = x + k as u32 * 4 * scale;
            for (row, bits) in DIGITS[d].iter().enumerate() {
                for col in 0..3 {
                    if bits & (0b100 >> col) != 0 {
                        self.rect(
                            dx + col * scale,
                            y + row as u32 * scale,
                            scale,
                            scale,
                            c,
                        );
                    }
                }
            }
        }
        digits.len() as u32 * 4 * scale - scale
    }
}

/// Where the bouncing square's left edge is after `steps` steps: one pixel
/// per step, back and forth along its track.
pub fn square_x(steps: u64) -> u32 {
    let span = (TRACK_RIGHT - TRACK_LEFT - SQUARE) as u64;
    let p = steps % (2 * span);
    let offset = if p <= span { p } else { 2 * span - p };
    TRACK_LEFT + offset as u32
}

/// Draws the whole picture into `pixels` (see [`BYTES`]).
///
/// `steps` is the number of fixed 1/60 s steps so far (white number, top
/// left); `frames` is the number of pictures the host has drawn (yellow
/// number below it). On a 60 Hz screen they climb together; on a 144 Hz
/// screen the yellow one climbs about 2.4 times faster.
pub fn render(steps: u64, frames: u64, pixels: &mut [u8]) {
    assert_eq!(pixels.len(), BYTES, "wrong picture size");
    let mut c = Canvas { pixels };
    c.rect(0, 0, WIDTH, HEIGHT, BLACK);

    // Faint grid: every 10 pixels, brighter every 50.
    for x in (0..WIDTH).step_by(10) {
        let v = if x % 50 == 0 { 60 } else { 20 };
        c.rect(x, 0, 1, HEIGHT, [v, v, v]);
    }
    for y in (0..HEIGHT).step_by(10) {
        let v = if y % 50 == 0 { 60 } else { 20 };
        c.rect(0, y, WIDTH, 1, [v, v, v]);
    }

    // The two counters sit on a black plate so the grid does not cut them.
    c.rect(4, 4, 150, 38, BLACK);
    c.number(steps, 8, 6, 3, WHITE);
    c.number(frames, 8, 24, 3, YELLOW);

    // Grey ramp: 16 steps, 0, 17, 34 ... 255.
    for i in 0..16u32 {
        let v = (i * 17) as u8;
        c.rect(20 + i * 24, 48, 24, 16, [v, v, v]);
    }
    // Colour bars: red, green, blue, white, cyan, magenta, yellow, black.
    let bars: [Rgb; 8] = [
        [255, 0, 0],
        [0, 255, 0],
        [0, 0, 255],
        [255, 255, 255],
        [0, 255, 255],
        [255, 0, 255],
        [255, 255, 0],
        [0, 0, 0],
    ];
    for (i, b) in bars.iter().enumerate() {
        c.rect(20 + i as u32 * 24, 68, 24, 16, *b);
    }
    // A flat grey 128 patch (its exact value can be read back from the
    // canvas) next to a one-pixel black and white checker, which turns to
    // smeared grey if the picture is scaled with smoothing.
    c.rect(20, 92, 32, 32, [128, 128, 128]);
    for y in 0..32 {
        for x in 0..32 {
            let v = if (x + y) % 2 == 0 { 255 } else { 0 };
            c.put(56 + x, 92 + y, [v, v, v]);
        }
    }
    // Vertical and horizontal one-pixel lines, each pair two pixels apart:
    // uneven thickness would show a fractional zoom.
    for k in 0..8u32 {
        c.rect(100 + k * 3, 92, 1, 32, WHITE);
        c.rect(100, 128 + k * 3, 24, 1, WHITE);
    }

    // The bouncing square, one pixel per step.
    c.rect(TRACK_LEFT - 1, SQUARE_TOP - 4, 1, SQUARE + 8, WHITE);
    c.rect(TRACK_RIGHT, SQUARE_TOP - 4, 1, SQUARE + 8, WHITE);
    c.rect(square_x(steps), SQUARE_TOP, SQUARE, SQUARE, YELLOW);

    // A one-pixel white frame on the picture's outer edge. If it is
    // missing on a side, that side is cropped.
    c.rect(0, 0, WIDTH, 1, WHITE);
    c.rect(0, HEIGHT - 1, WIDTH, 1, WHITE);
    c.rect(0, 0, 1, HEIGHT, WHITE);
    c.rect(WIDTH - 1, 0, 1, HEIGHT, WHITE);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn card(steps: u64, frames: u64) -> Vec<u8> {
        let mut p = vec![7u8; BYTES];
        render(steps, frames, &mut p);
        p
    }

    fn px(p: &[u8], x: u32, y: u32) -> [u8; 4] {
        let i = ((y * WIDTH + x) * 4) as usize;
        [p[i], p[i + 1], p[i + 2], p[i + 3]]
    }

    #[test]
    fn every_pixel_is_written_and_opaque() {
        let p = card(0, 0);
        assert!(p.chunks(4).all(|c| c[3] == 255));
    }

    #[test]
    fn the_frame_is_on_all_four_edges() {
        let p = card(123, 456);
        for x in 0..WIDTH {
            assert_eq!(px(&p, x, 0), [255, 255, 255, 255]);
            assert_eq!(px(&p, x, HEIGHT - 1), [255, 255, 255, 255]);
        }
        for y in 0..HEIGHT {
            assert_eq!(px(&p, 0, y), [255, 255, 255, 255]);
            assert_eq!(px(&p, WIDTH - 1, y), [255, 255, 255, 255]);
        }
    }

    #[test]
    fn the_ramp_and_bars_have_the_exact_values() {
        let p = card(0, 0);
        assert_eq!(px(&p, 20, 50), [0, 0, 0, 255]);
        assert_eq!(px(&p, 20 + 24 * 15 + 5, 50), [255, 255, 255, 255]);
        assert_eq!(px(&p, 20 + 24 * 7, 50), [119, 119, 119, 255]);
        assert_eq!(px(&p, 25, 70), [255, 0, 0, 255]);
        assert_eq!(px(&p, 25 + 24 * 2, 70), [0, 0, 255, 255]);
        assert_eq!(px(&p, 30, 100), [128, 128, 128, 255]);
    }

    #[test]
    fn the_square_moves_one_pixel_per_step_and_turns_round() {
        assert_eq!(square_x(0), TRACK_LEFT);
        assert_eq!(square_x(1), TRACK_LEFT + 1);
        let span = (TRACK_RIGHT - TRACK_LEFT - SQUARE) as u64;
        assert_eq!(square_x(span), TRACK_RIGHT - SQUARE);
        assert_eq!(square_x(span + 1), TRACK_RIGHT - SQUARE - 1);
        assert_eq!(square_x(2 * span), TRACK_LEFT);
        // Same card for the same steps, different card a step later.
        assert_eq!(card(10, 5), card(10, 5));
        assert_ne!(card(10, 5), card(11, 5));
    }

    #[test]
    fn the_counters_draw_digits() {
        // Digit 1 at scale 3: its top row is 0b010, so the middle block of
        // the first digit is white and the left block is not.
        let p = card(1, 8);
        let mid = px(&p, 8 + 3, 6);
        let left = px(&p, 8, 6);
        assert_eq!(mid, [255, 255, 255, 255]);
        assert_ne!(left, [255, 255, 255, 255]);
        // The frame counter is yellow where its digit has a block.
        assert_eq!(px(&p, 8, 24), [255, 200, 0, 255]);
    }
}
