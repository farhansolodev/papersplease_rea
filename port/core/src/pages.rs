//! The font test pages of milestone 1a: the port's own test material, built
//! exactly as scripts/reference/fontpage.py builds them (see its header for
//! what each page shows). One text page per font id, then every font sheet
//! 570 x 320 at a time.
//!
//! The pictures a page needs live in a [`Gallery`], loaded from the start
//! pack. The gallery also holds the title screen's pictures and texts
//! (milestone 1b, `title.rs`).

use std::collections::HashMap;

use crate::font::{read_fonts_xml, Font};
use crate::pack::Pack;
use crate::picture::Picture;
use crate::raster::{Quad, Screen};
use crate::screen::{HEIGHT, WIDTH};
use crate::text::{Align, Text};

/// Fonts, pictures and texts, loaded once. Picture 0 is the 1 x 1 white one.
pub struct Gallery {
    /// Fonts by id, in the order of `Fonts.xml`.
    pub fonts: Vec<(String, Font)>,
    pub pictures: Vec<Picture>,
    /// The pack's `strings.json`: texts of `Text.xml` by id.
    pub strings: HashMap<String, String>,
    /// Picture index by name: a font sheet by its file name, any other
    /// picture as `pictures/<file name>`.
    names: HashMap<String, usize>,
    sheet_files: Vec<String>,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PageKind {
    /// Samples of one font id (an index into `Gallery::fonts`).
    Text(usize),
    /// Part `n` of a font sheet (an index into the sheet list).
    Sheet(usize, usize),
}

/// The text of a flat JSON object of strings, `{"key": "value", ...}`: the
/// only JSON the pack holds. Understands the usual backslash escapes.
fn json_strings(json: &str) -> HashMap<String, String> {
    let mut out = HashMap::new();
    let mut chars = json.chars();
    let read_string = |chars: &mut std::str::Chars| -> Option<String> {
        while chars.next()? != '"' {}
        let mut s = String::new();
        loop {
            match chars.next()? {
                '"' => return Some(s),
                '\\' => match chars.next()? {
                    'n' => s.push('\n'),
                    't' => s.push('\t'),
                    'r' => s.push('\r'),
                    'u' => {
                        let hex: String = (0..4).filter_map(|_| chars.next()).collect();
                        if let Some(c) = u32::from_str_radix(&hex, 16).ok().and_then(char::from_u32) {
                            s.push(c);
                        }
                    }
                    c => s.push(c),
                },
                c => s.push(c),
            }
        }
    };
    while let Some(key) = read_string(&mut chars) {
        let Some(value) = read_string(&mut chars) else { break };
        out.insert(key, value);
    }
    out
}

impl Gallery {
    pub fn from_pack(pack: &Pack) -> Result<Gallery, String> {
        let get = |name: &str| {
            pack.get(name)
                .ok_or_else(|| format!("{name} is missing from the pack"))
        };
        let text = |name: &str| -> Result<String, String> {
            String::from_utf8(get(name)?.to_vec()).map_err(|_| format!("{name} is not UTF-8"))
        };
        let strings = json_strings(&text("strings.json")?);
        let hyphen = strings.get("wrap_hyphen").cloned().unwrap_or_else(|| "-".into());
        let mut gallery = Gallery {
            fonts: Vec::new(),
            pictures: vec![Picture::white()],
            strings,
            names: HashMap::new(),
            sheet_files: Vec::new(),
        };
        for entry in read_fonts_xml(&text("data/Fonts.xml")?) {
            let font = Font::new(&entry.file, &text(&format!("fonts/{}.fnt", entry.file))?, entry.line_height, &hyphen);
            for file in &font.page_files {
                if !gallery.names.contains_key(file) {
                    let picture = Picture::from_png(get(&format!("fonts/{file}"))?)?;
                    gallery.names.insert(file.clone(), gallery.pictures.len());
                    gallery.pictures.push(picture);
                    gallery.sheet_files.push(file.clone());
                }
            }
            gallery.fonts.push((entry.id, font));
        }
        for name in pack.names().into_iter().filter(|n| n.starts_with("pictures/")) {
            let picture = Picture::from_png(get(name)?).map_err(|e| format!("{name}: {e}"))?;
            gallery.names.insert(name.to_string(), gallery.pictures.len());
            gallery.pictures.push(picture);
        }
        Ok(gallery)
    }

    pub fn font(&self, id: &str) -> Option<&Font> {
        self.fonts.iter().find(|(i, _)| i == id).map(|(_, f)| f)
    }

    /// The index of a picture of the pack's `pictures/` folder, by its file
    /// name (`Title.png`).
    pub fn picture(&self, file: &str) -> Option<usize> {
        self.names.get(&format!("pictures/{file}")).copied()
    }

    fn sheet(&self, index: usize) -> (&str, &Picture) {
        let name = &self.sheet_files[index];
        (name, &self.pictures[self.names[name]])
    }

    /// Every page, in order.
    pub fn pages(&self) -> Vec<PageKind> {
        let mut out: Vec<PageKind> = (0..self.fonts.len()).map(PageKind::Text).collect();
        for s in 0..self.sheet_files.len() {
            let (_, pic) = self.sheet(s);
            for n in 0..sheet_parts(pic.width, pic.height).len() {
                out.push(PageKind::Sheet(s, n));
            }
        }
        out
    }

    /// The quads of page `index`, in drawing order.
    pub fn build_page(&self, index: usize) -> Vec<Quad> {
        let pages = self.pages();
        let regular = self.font("regular").expect("font `regular`");
        let mut b = Builder { gallery: self, quads: Vec::new() };
        let tail = format!("  page {} of {}", index + 1, pages.len());
        match &pages[index] {
            PageKind::Text(f) => {
                let (id, font) = &self.fonts[*f];
                b.fill(0.0, 0.0, WIDTH as f64, HEIGHT as f64, 0xFF202830);
                b.text(
                    regular,
                    &format!(
                        "{} / {}: line {} ascent {} cap {} descent {} space {}{}",
                        id, font.name, font.line_height, font.ascent, font.cap_height,
                        font.descent(), font.space_width, tail
                    ),
                    4.0,
                    4.0,
                    |_| {},
                );
                let mut y = 20;
                y += b.text(font, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", 4.0, y as f64, |_| {}) + 4;
                y += b.text(font, "abcdefghijklmnopqrstuvwxyz", 4.0, y as f64, |t| t.color = 0xFFB0FFB0) + 4;
                y += b.text(font, "0123456789 .,:;!?'\"-+=()[]/%&#@*$", 4.0, y as f64, |t| t.color = 0xFFB0B0FF) + 4;
                y += b.text(font, "box \u{263a} \u{a7} end", 4.0, y as f64, |_| {}) + 4;
                y += b.text(font, "Rounded", 4.0, y as f64, |t| {
                    t.padding_x = 3;
                    t.padding_y = 2;
                    t.background = 0xFF3355AA;
                    t.rounded = true;
                }) + 4;
                y += b.text(font, "Plain box", 4.0, y as f64, |t| {
                    t.padding_x = 2;
                    t.padding_y = 1;
                    t.background = 0xFF883333;
                }) + 4;
                b.fill(4.0, y as f64, 150.0, font.line_height as f64, 0xFFFFFFFF);
                b.text(font, "Half alpha", 4.0, y as f64, |t| t.color = 0x80FF4020);
                let mut y = 20;
                let paragraph = "The quick brown fox jumps over the lazy dog. \
Pneumonoultramicroscopicsilicovolcanoconiosis is a very long word that gets cut with a hyphen.";
                y += b.text(font, paragraph, 290.0, y as f64, |t| {
                    t.fixed_width = 270;
                    t.multi_line = true;
                    t.color = 0xFFFFCC33;
                }) + 4;
                y += b.text(
                    font,
                    "Centred text\nwraps and\ncentres each line within the widest line",
                    290.0,
                    y as f64,
                    |t| {
                        t.fixed_width = 270;
                        t.multi_line = true;
                        t.align = Align::Center;
                        t.color = 0xFFCCFFFF;
                    },
                ) + 4;
                y += b.text(font, "Right aligned line one\nand a much longer second line", 290.0, y as f64, |t| {
                    t.fixed_width = 270;
                    t.multi_line = true;
                    t.align = Align::Right;
                    t.color = 0xFFFFCCCC;
                }) + 4;
                y += b.text(font, "Fractional 0.5", 290.5, y as f64 + 0.5, |_| {}) + 4;
                b.text(font, "one\ntwo\nthree", 290.0, y as f64, |t| {
                    t.multi_line = true;
                    t.line_spacing = 3;
                });
            }
            PageKind::Sheet(s, n) => {
                let (name, pic) = self.sheet(*s);
                let parts = sheet_parts(pic.width, pic.height);
                let (ox, oy) = parts[*n];
                b.fill(0.0, 0.0, WIDTH as f64, HEIGHT as f64, 0xFF303848);
                b.quads.push(Quad {
                    image: self.names[name],
                    x0: -ox as f64,
                    y0: -oy as f64,
                    x1: -ox as f64 + pic.width as f64,
                    y1: -oy as f64 + pic.height as f64,
                    src: [0, 0, pic.width as i32, pic.height as i32],
                    color: 0xFFFFFFFF,
                });
                b.text(
                    regular,
                    &format!("{}  {} x {}  part {} of {}{}", name, pic.width, pic.height, n + 1, parts.len(), tail),
                    0.0,
                    0.0,
                    |t| {
                        t.padding_x = 2;
                        t.padding_y = 1;
                        t.background = 0xC0000000;
                    },
                );
            }
        }
        b.quads
    }

    /// Draws page `index` into `screen` (cleared first).
    pub fn draw_page(&self, index: usize, screen: &mut Screen) {
        screen.clear();
        for q in self.build_page(index) {
            screen.draw(&q, &self.pictures);
        }
    }
}

/// Offsets of the 570 x 320 windows over a sheet, row by row.
fn sheet_parts(width: u32, height: u32) -> Vec<(i32, i32)> {
    let cols = width.div_ceil(WIDTH);
    let rows = height.div_ceil(HEIGHT);
    (0..cols * rows)
        .map(|p| ((p % cols * WIDTH) as i32, (p / cols * HEIGHT) as i32))
        .collect()
}

/// Collects the quads of one picture, in drawing order.
pub(crate) struct Builder<'a> {
    pub(crate) gallery: &'a Gallery,
    pub(crate) quads: Vec<Quad>,
}

impl Builder<'_> {
    pub(crate) fn fill(&mut self, x: f64, y: f64, w: f64, h: f64, color: u32) {
        self.quads.push(Quad { image: 0, x0: x, y0: y, x1: x + w, y1: y + h, src: [0, 0, 1, 1], color });
    }

    /// Draws a text at (x, y) and returns its height. `set` changes the
    /// settings of a new text whose colour starts white.
    pub(crate) fn text(&mut self, font: &Font, string: &str, x: f64, y: f64, set: impl FnOnce(&mut Text)) -> i32 {
        let mut t = Text::new(string);
        t.color = 0xFFFFFFFF;
        set(&mut t);
        let built = t.build(font);
        for tile in &built.tiles {
            let (w, h) = (tile.dst[2] as f64, tile.dst[3] as f64);
            let x0 = x + tile.dst[0] as f64;
            let y0 = y + tile.dst[1] as f64;
            let image = match tile.page {
                None => 0,
                Some(p) => self.gallery.names[&font.page_files[p]],
            };
            self.quads.push(Quad { image, x0, y0, x1: x0 + w, y1: y0 + h, src: tile.src, color: tile.color });
        }
        built.height
    }

    /// A sprite of the piece `src` (x, y, width, height) of picture `image`,
    /// drawn at (x, y) at its own size.
    pub(crate) fn part(&mut self, image: usize, x: f64, y: f64, src: [i32; 4]) {
        let (x1, y1) = (x + src[2] as f64, y + src[3] as f64);
        self.quads.push(Quad { image, x0: x, y0: y, x1, y1, src, color: 0xFFFFFFFF });
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_the_pack_strings() {
        let m = json_strings(r#"{"wrap_hyphen": "-", "b": "a\"b\\cA"}"#);
        assert_eq!(m["wrap_hyphen"], "-");
        assert_eq!(m["b"], "a\"b\\cA");
    }

    #[test]
    fn sheets_are_cut_into_screen_sized_parts() {
        assert_eq!(sheet_parts(284, 287), [(0, 0)]);
        assert_eq!(sheet_parts(592, 576), [(0, 0), (570, 0), (0, 320), (570, 320)]);
        assert_eq!(sheet_parts(570, 320), [(0, 0)]);
        assert_eq!(sheet_parts(571, 320), [(0, 0), (570, 0)]);
    }
}
