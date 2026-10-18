//! Fonts: the `.fnt` description of a bitmap font, its measurements and the
//! line breaker (`app.vis.Font`, docs/fonts.md). Follows the reference in
//! scripts/reference/fonts.py step by step.

use std::collections::{HashMap, VecDeque};

use crate::xmlscan;

#[derive(Debug, Clone)]
pub struct Letter {
    /// The sheet the letter is on (an index into the font's page files).
    pub page: usize,
    /// x, y, width, height on the sheet.
    pub rect: [i32; 4],
    /// Where to draw it, relative to the pen (the y already moved so the
    /// highest letter of the font sits at 0).
    pub offset: [i32; 2],
    pub advance: i32,
}

#[derive(Debug)]
pub struct Font {
    /// The font file's name without its ending (`bmmini_u_regular_8`).
    pub name: String,
    /// The sheet pictures, as named in the file (`bmmini_u_regular_8.png`).
    pub page_files: Vec<String>,
    letters: HashMap<u32, Letter>,
    pub line_height: i32,
    pub advance_max: i32,
    pub space_width: i32,
    pub ascent: i32,
    pub cap_height: i32,
    hyphen: String,
    hyphen_width: i32,
}

pub struct Line {
    pub text: String,
    pub width: i32,
}

/// What `Font.split` returns.
pub struct Split {
    pub lines: Vec<Line>,
    pub hyphenated: bool,
    /// The widest line, measured before a one-line text drops the others.
    pub widest: i32,
    /// Characters that are not spaces, in the lines kept.
    pub glyphs: usize,
}

/// Haxe's `Std.parseInt` as the font code uses it: a missing or bad number
/// counts as 0.
fn parse_int(s: Option<&str>) -> i32 {
    let s = s.unwrap_or("").trim_start();
    let mut end = 0;
    for (i, c) in s.char_indices() {
        if c.is_ascii_digit() || (i == 0 && (c == '+' || c == '-')) {
            end = i + c.len_utf8();
        } else {
            break;
        }
    }
    s[..end].parse().unwrap_or(0)
}

impl Font {
    /// `fnt` is the text of the `.fnt` file. `force_line_height` is the
    /// `lineheight` of the `Fonts.xml` entry (0 = work it out from the
    /// letters). `hyphen` is the language's `wrap_hyphen` text.
    pub fn new(name: &str, fnt: &str, force_line_height: i32, hyphen: &str) -> Font {
        let tags = xmlscan::tags(fnt);
        let page_files = tags
            .iter()
            .filter(|t| t.name == "page")
            .map(|t| t.attr("file").unwrap_or("").to_string())
            .collect();
        let mut letters = HashMap::new();
        let (mut line_height, mut advance_max, mut space_width) = (0, 0, 0);
        let mut reference: Option<u32> = None;
        let mut top = 10000;
        for tag in tags.iter().filter(|t| t.name == "char") {
            let mut text = tag.attr("letter").unwrap_or("").to_string();
            if text == "space" {
                text = " ".into();
            }
            let Some(first) = text.chars().next() else { continue };
            let code = first as u32;
            let letter = Letter {
                page: parse_int(tag.attr("page")).max(0) as usize,
                rect: [
                    parse_int(tag.attr("x")),
                    parse_int(tag.attr("y")),
                    parse_int(tag.attr("width")),
                    parse_int(tag.attr("height")),
                ],
                offset: [parse_int(tag.attr("xoffset")), parse_int(tag.attr("yoffset"))],
                advance: parse_int(tag.attr("xadvance")),
            };
            // The reference measurements come from the last "0" or "A".
            if text == "0" || text == "A" {
                reference = Some(code);
            }
            line_height = line_height.max(letter.rect[3]);
            advance_max = advance_max.max(letter.advance);
            top = top.min(letter.offset[1]);
            if text == " " {
                space_width = letter.advance;
            }
            letters.insert(code, letter);
        }
        for letter in letters.values_mut() {
            letter.offset[1] -= top;
        }
        let (mut ascent, mut cap_height) = (0, 0);
        if let Some(r) = reference.and_then(|c| letters.get(&c)) {
            ascent = r.offset[1] + r.rect[3];
            cap_height = r.rect[3];
        }
        if force_line_height != 0 {
            line_height = force_line_height;
        }
        let hyphen = if hyphen == "NONE" { String::new() } else { hyphen.to_string() };
        let mut font = Font {
            name: name.to_string(),
            page_files,
            letters,
            line_height,
            advance_max,
            space_width,
            ascent,
            cap_height,
            hyphen,
            hyphen_width: 0,
        };
        font.hyphen_width = font.text_width(&font.hyphen.clone());
        font
    }

    pub fn descent(&self) -> i32 {
        self.line_height - self.ascent
    }

    pub fn letter(&self, c: char) -> Option<&Letter> {
        self.letters.get(&(c as u32))
    }

    pub fn letter_count(&self) -> usize {
        self.letters.len()
    }

    /// Sum of the advances; characters the font lacks count as 0.
    pub fn text_width(&self, text: &str) -> i32 {
        text.chars()
            .filter_map(|c| self.letter(c))
            .map(|l| l.advance)
            .sum()
    }

    /// `Font.split`: breaks `text` into lines no wider than `max_width`
    /// (0 = only at line breaks). See docs/fonts.md, "Measuring and breaking
    /// text"; its order of steps is a reconstruction, not tested against
    /// the game at the edges.
    pub fn split(&self, text: &str, max_width: i32, multi_line: bool) -> Split {
        let mut lines: Vec<Line> = Vec::new();
        let mut hyphenated = false;
        let flush = |lines: &mut Vec<Line>, line: &str| {
            let line = line.trim_end();
            lines.push(Line { text: line.to_string(), width: self.text_width(line) });
        };
        if max_width == 0 {
            for part in text.split('\n') {
                let part = part.trim();
                lines.push(Line { text: part.to_string(), width: self.text_width(part) });
            }
        } else {
            let max_width = max_width.max(self.advance_max);
            let mut current = String::new();
            let mut width = 0;
            for paragraph in text.split('\n') {
                let mut words: VecDeque<String> = paragraph.split(' ').map(String::from).collect();
                // Guards a pathological case (not one letter fits with a
                // hyphen), which would otherwise repeat for ever: after
                // two empty lines in a row one letter is taken anyway.
                let mut stuck = 0;
                while let Some(word) = words.front().cloned() {
                    let word_width = self.text_width(&word);
                    if word_width + width < max_width {
                        current.push_str(&word);
                        current.push(' ');
                        width += self.space_width + word_width;
                        words.pop_front();
                        stuck = 0;
                        if !words.is_empty() {
                            continue;
                        }
                    } else if word_width >= max_width {
                        let chars: Vec<char> = word.chars().collect();
                        let mut count = 0;
                        while count < chars.len() {
                            let head: String = chars[..count + 1].iter().collect();
                            if self.text_width(&head) + width + self.hyphen_width >= max_width {
                                break;
                            }
                            count += 1;
                        }
                        if count == 0 && width == 0 {
                            stuck += 1;
                            if stuck >= 2 {
                                count = 1;
                            }
                        }
                        if count > 0 {
                            let head: String = chars[..count].iter().collect();
                            words[0] = chars[count..].iter().collect();
                            current.push_str(&head);
                            if !head.ends_with(&self.hyphen) || self.hyphen.is_empty() {
                                current.push_str(&self.hyphen);
                            }
                            hyphenated = true;
                            stuck = 0;
                        }
                    }
                    flush(&mut lines, &current);
                    current.clear();
                    width = 0;
                }
            }
            if !current.trim_end().is_empty() {
                flush(&mut lines, &current);
            }
        }
        let widest = lines.iter().map(|l| l.width).max().unwrap_or(0);
        if !multi_line && lines.len() > 1 {
            lines.truncate(1);
        }
        let glyphs = lines
            .iter()
            .map(|l| l.text.chars().filter(|&c| c != ' ').count())
            .sum();
        Split { lines, hyphenated, widest, glyphs }
    }
}

/// The font table of `Fonts.xml`: id, file, forced line height, in file
/// order.
pub struct FontEntry {
    pub id: String,
    pub file: String,
    pub line_height: i32,
}

pub fn read_fonts_xml(xml: &str) -> Vec<FontEntry> {
    xmlscan::tags(xml)
        .iter()
        .filter(|t| t.name == "font")
        .map(|t| FontEntry {
            id: t.attr("id").unwrap_or("").to_string(),
            file: t.attr("file").unwrap_or("").to_string(),
            line_height: parse_int(t.attr("lineheight")),
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    // A font of five letters: space (advance 2), A, B (advance 4), '-' (advance 3), 0.
    const FNT: &str = r#"<font><pages><page id="0" file="t.png"/></pages><chars count="5">
 <char letter="space" page="0" x="0" y="0" width="0" height="0" xoffset="0" yoffset="9" xadvance="2"/>
 <char letter="A" page="0" x="1" y="1" width="3" height="6" xoffset="0" yoffset="3" xadvance="4"/>
 <char letter="B" page="0" x="5" y="1" width="3" height="6" xoffset="0" yoffset="4" xadvance="4"/>
 <char letter="-" page="0" x="9" y="1" width="2" height="1" xoffset="0" yoffset="6" xadvance="3"/>
 <char letter="0" page="0" x="12" y="1" width="3" height="5" xoffset="1" yoffset="3" xadvance="4"/>
</chars></font>"#;

    fn font() -> Font {
        Font::new("t", FNT, 0, "-")
    }

    #[test]
    fn measures_the_font() {
        let f = font();
        // Tallest rectangle 6; widest advance 4; space 2; top = smallest
        // yoffset 3, taken off every letter; the last "0"/"A" is the "0"
        // (offset 3 - 3 = 0, height 5) so ascent 5, cap 5, descent 1.
        assert_eq!((f.line_height, f.advance_max, f.space_width), (6, 4, 2));
        assert_eq!((f.ascent, f.cap_height, f.descent()), (5, 5, 1));
        assert_eq!(f.letter('B').unwrap().offset, [0, 1]);
        assert_eq!(f.page_files, ["t.png"]);
        assert_eq!(font_with_height().line_height, 9);
    }

    fn font_with_height() -> Font {
        Font::new("t", FNT, 9, "-")
    }

    #[test]
    fn width_skips_unknown_characters() {
        assert_eq!(font().text_width("AB?A"), 12);
    }

    #[test]
    fn splits_at_line_breaks_only_when_the_width_is_zero() {
        let s = font().split(" AB \nA", 0, true);
        let t: Vec<_> = s.lines.iter().map(|l| (l.text.as_str(), l.width)).collect();
        assert_eq!(t, [("AB", 8), ("A", 4)]);
        assert_eq!(s.widest, 8);
        // One line only: the widest is still measured before the cut.
        let s = font().split("A\nAB", 0, false);
        assert_eq!((s.lines.len(), s.widest, s.glyphs), (1, 8, 1));
    }

    #[test]
    fn wraps_words_and_cuts_long_ones_with_a_hyphen() {
        let f = font();
        // Limit 11: "AB" (8) fits; adding "AB" would need 8 + 2 + 8 > 11.
        let s = f.split("AB AB", 11, true);
        let t: Vec<_> = s.lines.iter().map(|l| l.text.as_str()).collect();
        assert_eq!(t, ["AB", "AB"]);
        assert!(!s.hyphenated);
        // A word as wide as the limit is cut: with limit 12, "ABAB" (16)
        // keeps letters while letters + hyphen (3) stay under 12: "ABA"
        // (12) does not fit, "AB" (8) + 3 = 11 does.
        let s = f.split("ABAB", 12, true);
        let t: Vec<_> = s.lines.iter().map(|l| l.text.as_str()).collect();
        assert_eq!(t, ["AB-", "AB"]);
        assert!(s.hyphenated);
    }

    #[test]
    fn the_limit_is_never_below_the_widest_advance() {
        let f = font();
        let texts = |limit| {
            f.split("AB A", limit, true)
                .lines
                .iter()
                .map(|l| l.text.clone())
                .collect::<Vec<_>>()
        };
        assert_eq!(texts(1), texts(4));
        assert_ne!(texts(4), texts(5));
    }

    #[test]
    fn a_limit_too_small_for_a_letter_and_hyphen_still_ends() {
        let f = Font::new("t", FNT, 0, "-");
        // Limit 4 = widest advance; "AB" is 8 wide, a letter (4) + hyphen (3) is 7.
        let s = f.split("AB", 4, true);
        assert!(!s.lines.is_empty() && s.lines.len() < 10);
    }

    #[test]
    fn reads_fonts_xml_with_comments() {
        let xml = r#"<fonts><!--<font id="gone" file="x"/>--><font id="a" file="f" lineheight="8"/><font id="b" file="f"/></fonts>"#;
        let e = read_fonts_xml(xml);
        assert_eq!(e.len(), 2);
        assert_eq!((e[0].id.as_str(), e[0].line_height), ("a", 8));
        assert_eq!((e[1].file.as_str(), e[1].line_height), ("f", 0));
    }

    #[test]
    fn parse_int_is_forgiving() {
        assert_eq!(parse_int(Some(" 12abc")), 12);
        assert_eq!(parse_int(Some("-3")), -3);
        assert_eq!(parse_int(Some("x")), 0);
        assert_eq!(parse_int(None), 0);
    }
}
