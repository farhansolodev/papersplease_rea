//! Drawing quads into the 570 x 320 screen picture, in software.
//!
//! The rules are the reference's (scripts/reference/host.py) so the pixels
//! can be compared byte for byte; they are the game's own where the Unity
//! files say so and **assumptions about the graphics card** where they do
//! not (docs/screen-output.md, "For the port"):
//!
//! - which pixels a quad covers: pixel `i` when its centre `i + 0.5` lies in
//!   `[p0, p1)` (assumed);
//! - which texel a pixel reads: its centre mapped into the picture's
//!   coordinates, rounded down, held inside the picture (nearest-pixel
//!   reads, clamped edges; assumed);
//! - the pixel: texel x colour, then ordinary alpha blending on the stored
//!   values, no colour-space conversion (read from the quad shader);
//! - 8-bit rounding: to the nearest step (assumed).
//!
//! All arithmetic is in `f64`, in the same order as the Python reference.

use crate::picture::Picture;
use crate::screen::{HEIGHT, WIDTH};

/// Quad.kAlphaThresh: a quad whose colour alpha is smaller is not drawn.
const ALPHA_THRESH: f64 = 0.001;

/// One picture piece to draw: a rectangle on the screen, in game pixels
/// (fractions allowed), reading a rectangle of a picture, tinted by a colour.
#[derive(Debug, Clone, PartialEq)]
pub struct Quad {
    /// Which picture (an index into the list given to [`Screen::draw`]).
    pub image: usize,
    pub x0: f64,
    pub y0: f64,
    pub x1: f64,
    pub y1: f64,
    /// x, y, width, height of the piece on the picture, in pixels.
    pub src: [i32; 4],
    /// 0xAARRGGBB.
    pub color: u32,
}

/// The screen picture: `WIDTH x HEIGHT` pixels of red, green, blue, alpha
/// bytes, cleared to opaque black.
pub struct Screen {
    pub pixels: Vec<u8>,
}

fn covered(p0: f64, p1: f64, limit: u32) -> std::ops::Range<u32> {
    let first = (p0 - 0.5).ceil().max(0.0);
    let last = (p1 - 0.5).ceil() - 1.0; // the last pixel, counted from 0
    let end = (last + 1.0).min(limit as f64);
    if end <= first {
        0..0
    } else {
        first as u32..end as u32
    }
}

fn texel_at(i: u32, p0: f64, p1: f64, u0: f64, u1: f64, size: u32) -> u32 {
    let u = u0 + (i as f64 + 0.5 - p0) / (p1 - p0) * (u1 - u0);
    let t = (u * size as f64).floor();
    t.clamp(0.0, (size - 1) as f64) as u32
}

fn to_byte(f: f64) -> u8 {
    (f.clamp(0.0, 1.0) * 255.0 + 0.5).floor() as u8
}

impl Default for Screen {
    fn default() -> Self {
        Self::new()
    }
}

impl Screen {
    pub fn new() -> Screen {
        let mut s = Screen { pixels: vec![0; (WIDTH * HEIGHT * 4) as usize] };
        s.clear();
        s
    }

    /// Clears to opaque black (the start of every frame).
    pub fn clear(&mut self) {
        for p in self.pixels.chunks_exact_mut(4) {
            p.copy_from_slice(&[0, 0, 0, 255]);
        }
    }

    pub fn draw(&mut self, q: &Quad, pictures: &[Picture]) {
        if (q.color >> 24) as f64 / 255.0 < ALPHA_THRESH {
            return;
        }
        let pic = &pictures[q.image];
        let colour = [
            ((q.color >> 16) & 255) as f64 / 255.0,
            ((q.color >> 8) & 255) as f64 / 255.0,
            (q.color & 255) as f64 / 255.0,
            (q.color >> 24) as f64 / 255.0,
        ];
        let [sx, sy, sw, sh] = q.src;
        let (iw, ih) = (pic.width as f64, pic.height as f64);
        let (u0, u1) = (sx as f64 / iw, (sx + sw) as f64 / iw);
        let (v0, v1) = (sy as f64 / ih, (sy + sh) as f64 / ih);
        let xs = covered(q.x0, q.x1, WIDTH);
        for y in covered(q.y0, q.y1, HEIGHT) {
            let ty = texel_at(y, q.y0, q.y1, v0, v1, pic.height);
            for x in xs.clone() {
                let tx = texel_at(x, q.x0, q.x1, u0, u1, pic.width);
                let texel = pic.texel(tx, ty);
                let c: [f64; 4] = std::array::from_fn(|i| texel[i] as f64 / 255.0 * colour[i]);
                let a = c[3];
                let at = ((y * WIDTH + x) * 4) as usize;
                for i in 0..3 {
                    let under = self.pixels[at + i] as f64 / 255.0;
                    self.pixels[at + i] = to_byte(c[i] * a + under * (1.0 - a));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn white() -> Vec<Picture> {
        vec![Picture::white()]
    }

    fn quad(x0: f64, y0: f64, x1: f64, y1: f64, color: u32) -> Quad {
        Quad { image: 0, x0, y0, x1, y1, src: [0, 0, 1, 1], color }
    }

    fn px(s: &Screen, x: u32, y: u32) -> [u8; 4] {
        let i = ((y * WIDTH + x) * 4) as usize;
        [s.pixels[i], s.pixels[i + 1], s.pixels[i + 2], s.pixels[i + 3]]
    }

    #[test]
    fn a_whole_pixel_quad_covers_exactly_its_pixels() {
        let mut s = Screen::new();
        s.draw(&quad(2.0, 3.0, 5.0, 4.0, 0xFF102030), &white());
        for x in 0..8 {
            let inside = (2..5).contains(&x);
            assert_eq!(px(&s, x, 3), if inside { [0x10, 0x20, 0x30, 255] } else { [0, 0, 0, 255] }, "x {x}");
        }
        assert_eq!(px(&s, 3, 2), [0, 0, 0, 255]);
        assert_eq!(px(&s, 3, 4), [0, 0, 0, 255]);
    }

    #[test]
    fn a_half_pixel_position_rounds_by_the_pixel_centre_rule() {
        let mut s = Screen::new();
        // x 2.5 .. 4.5: centres 2.5 (in: 2.5 >= 2.5), 3.5, and 4.5 (out: 4.5 < 4.5 is false)
        s.draw(&quad(2.5, 0.0, 4.5, 1.0, 0xFFFFFFFF), &white());
        assert_eq!(px(&s, 1, 0)[0], 0);
        assert_eq!(px(&s, 2, 0)[0], 255);
        assert_eq!(px(&s, 3, 0)[0], 255);
        assert_eq!(px(&s, 4, 0)[0], 0);
    }

    #[test]
    fn quads_running_off_the_screen_are_cut() {
        let mut s = Screen::new();
        s.draw(&quad(-10.0, -10.0, 2.0, 2.0, 0xFFFFFFFF), &white());
        s.draw(&quad(568.0, 318.0, 700.0, 900.0, 0xFFFFFFFF), &white());
        assert_eq!(px(&s, 0, 0)[0], 255);
        assert_eq!(px(&s, 1, 1)[0], 255);
        assert_eq!(px(&s, 2, 2)[0], 0);
        assert_eq!(px(&s, 569, 319)[0], 255);
        assert_eq!(px(&s, 567, 319)[0], 0);
    }

    #[test]
    fn alpha_blends_on_the_stored_values() {
        let mut s = Screen::new();
        s.draw(&quad(0.0, 0.0, 1.0, 1.0, 0xFFFFFFFF), &white());
        // 0x80 = 128 alpha over white with red 255, green 0, blue 0:
        // a = 128/255; green = 0*a + 1*(1-a) = 127/255 -> 127
        s.draw(&quad(0.0, 0.0, 1.0, 1.0, 0x80FF0000), &white());
        assert_eq!(px(&s, 0, 0), [255, 127, 127, 255]);
    }

    #[test]
    fn a_transparent_colour_draws_nothing() {
        let mut s = Screen::new();
        s.draw(&quad(0.0, 0.0, 5.0, 5.0, 0x00FFFFFF), &white());
        assert_eq!(px(&s, 1, 1), [0, 0, 0, 255]);
    }

    #[test]
    fn a_stretched_picture_reads_nearest_pixels() {
        // A 2 x 1 picture: red, then blue. Stretched over 4 pixels: 2 each.
        let pic = Picture {
            width: 2,
            height: 1,
            rgba: vec![255, 0, 0, 255, 0, 0, 255, 255],
        };
        let mut s = Screen::new();
        let q = Quad { image: 0, x0: 10.0, y0: 0.0, x1: 14.0, y1: 1.0, src: [0, 0, 2, 1], color: 0xFFFFFFFF };
        s.draw(&q, &[pic]);
        assert_eq!(&px(&s, 10, 0)[..3], [255, 0, 0]);
        assert_eq!(&px(&s, 11, 0)[..3], [255, 0, 0]);
        assert_eq!(&px(&s, 12, 0)[..3], [0, 0, 255]);
        assert_eq!(&px(&s, 13, 0)[..3], [0, 0, 255]);
    }

    #[test]
    fn a_piece_of_a_picture_reads_only_its_rectangle() {
        let pic = Picture {
            width: 4,
            height: 1,
            rgba: vec![255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255, 9, 9, 9, 255],
        };
        let mut s = Screen::new();
        let q = Quad { image: 0, x0: 0.0, y0: 0.0, x1: 2.0, y1: 1.0, src: [1, 0, 2, 1], color: 0xFFFFFFFF };
        s.draw(&q, &[pic]);
        assert_eq!(&px(&s, 0, 0)[..3], [0, 255, 0]);
        assert_eq!(&px(&s, 1, 0)[..3], [0, 0, 255]);
    }

    #[test]
    fn an_empty_quad_covers_nothing() {
        let mut s = Screen::new();
        s.draw(&quad(3.0, 3.0, 3.0, 9.0, 0xFFFFFFFF), &white());
        s.draw(&quad(3.2, 3.2, 3.4, 9.0, 0xFFFFFFFF), &white());
        assert_eq!(px(&s, 3, 3), [0, 0, 0, 255]);
    }
}
