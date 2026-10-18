//! Laying out a text (`app.vis.Text.buildTiles`, docs/text-drawing.md).
//! Follows scripts/reference/text.py: the text becomes tiles, pieces of the
//! font sheet (or a stretched white pixel for boxes and backgrounds) with
//! their place relative to the text's own position.

use crate::font::Font;

/// The code of the space (`Font.kSpaceCharCode`): it gets no tile.
const SPACE: char = ' ';

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Align {
    Left,
    Center,
    Right,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum TileKind {
    /// A piece of a font sheet.
    Letter,
    /// A letter the font lacks: a filled box in the text colour.
    Box,
    /// The filled box behind the text.
    Background,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Tile {
    pub kind: TileKind,
    /// The sheet for a letter; none for the white 1 x 1 picture.
    pub page: Option<usize>,
    /// x, y, width, height of the piece on its picture.
    pub src: [i32; 4],
    /// x, y, width, height where it goes, relative to the text's position.
    pub dst: [i32; 4],
    /// 0xAARRGGBB.
    pub color: u32,
}

/// A text and its settings. As in the game, a new text has colour 0, which
/// is fully transparent: **it draws no letters until a colour is set**.
#[derive(Debug, Clone)]
pub struct Text {
    pub text: String,
    /// The line breaker's limit; 0 breaks only at line breaks.
    pub fixed_width: i32,
    /// False keeps only the first line.
    pub multi_line: bool,
    pub align: Align,
    pub padding_x: i32,
    pub padding_y: i32,
    pub line_spacing: i32,
    pub color: u32,
    pub background: u32,
    pub rounded: bool,
}

pub struct Built {
    pub tiles: Vec<Tile>,
    pub width: i32,
    pub height: i32,
    pub hyphenated: bool,
}

impl Text {
    pub fn new(text: &str) -> Text {
        Text {
            text: text.to_string(),
            fixed_width: 0,
            multi_line: false,
            align: Align::Left,
            padding_x: 0,
            padding_y: 0,
            line_spacing: 0,
            color: 0,
            background: 0,
            rounded: false,
        }
    }

    pub fn build(&self, font: &Font) -> Built {
        if self.text.is_empty() {
            return Built { tiles: Vec::new(), width: 0, height: 0, hyphenated: false };
        }
        let split = font.split(&self.text, self.fixed_width, self.multi_line);
        let r = i32::from(self.rounded);
        let mut tiles = Vec::new();
        let mut y = self.padding_y;
        for line in &split.lines {
            let mut x = self.padding_x;
            match self.align {
                Align::Center => x += (split.widest - line.width) / 2, // never negative
                Align::Right => x += split.widest - line.width,
                Align::Left => {}
            }
            x += r;
            for c in line.text.chars() {
                match font.letter(c) {
                    None => {
                        if c != SPACE {
                            tiles.push(Tile {
                                kind: TileKind::Box,
                                page: None,
                                src: [0, 0, 1, 1],
                                dst: [x + font.space_width - 1, y, font.space_width, font.cap_height],
                                color: self.color,
                            });
                        }
                        x += font.space_width;
                    }
                    Some(letter) => {
                        if c != SPACE {
                            tiles.push(Tile {
                                kind: TileKind::Letter,
                                page: Some(letter.page),
                                src: letter.rect,
                                dst: [
                                    x + letter.offset[0],
                                    y + letter.offset[1],
                                    letter.rect[2],
                                    letter.rect[3],
                                ],
                                color: self.color,
                            });
                        }
                        x += letter.advance;
                    }
                }
            }
            y += font.line_height + self.line_spacing;
        }
        let width = split.widest + 2 * self.padding_x;
        let n = split.lines.len() as i32;
        let height = font.line_height * n + self.line_spacing * (n - 1).max(0) + 2 * self.padding_y;
        if self.background >> 24 != 0 {
            let back = |dst: [i32; 4]| Tile {
                kind: TileKind::Background,
                page: None,
                src: [0, 0, 1, 1],
                dst,
                color: self.background,
            };
            let mut front = vec![back([r, 0, width - r, height])];
            if self.rounded {
                front.push(back([0, 1, r, height - 2]));
                front.push(back([width, 1, r, height - 2]));
            }
            front.append(&mut tiles); // the background tiles come first
            tiles = front;
        }
        Built { tiles, width: width + r, height, hyphenated: split.hyphenated }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const FNT: &str = r#"<font><pages><page id="0" file="t.png"/></pages><chars>
 <char letter="space" page="0" x="0" y="0" width="0" height="0" xoffset="0" yoffset="3" xadvance="2"/>
 <char letter="A" page="0" x="1" y="1" width="3" height="6" xoffset="0" yoffset="3" xadvance="4"/>
 <char letter="B" page="0" x="5" y="1" width="3" height="6" xoffset="1" yoffset="4" xadvance="4"/>
</chars></font>"#;

    fn font() -> Font {
        Font::new("t", FNT, 0, "-")
    }

    fn text(s: &str) -> Text {
        let mut t = Text::new(s);
        t.color = 0xFFFFFFFF;
        t
    }

    #[test]
    fn letters_get_tiles_spaces_do_not() {
        let b = text("A B").build(&font());
        // line height 6, widest line: 4 + 2 + 4 = 10
        assert_eq!((b.width, b.height), (10, 6));
        assert_eq!(b.tiles.len(), 2);
        assert_eq!(b.tiles[0].dst, [0, 0, 3, 6]);
        // B: pen at 4 + 2 = 6, plus xoffset 1; yoffset 4 - top 3 = 1
        assert_eq!(b.tiles[1].dst, [7, 1, 3, 6]);
        assert_eq!(b.tiles[1].src, [5, 1, 3, 6]);
        assert_eq!(b.tiles[1].page, Some(0));
    }

    #[test]
    fn a_missing_letter_is_a_box_that_overlaps_the_next_letter() {
        let b = text("?A").build(&font());
        // space width 2, cap height: reference letter is "A" (height 6)
        assert_eq!(b.tiles[0].kind, TileKind::Box);
        assert_eq!(b.tiles[0].dst, [1, 0, 2, 6]);
        assert_eq!(b.tiles[1].dst, [2, 0, 3, 6]); // the pen moved by 2 only
    }

    #[test]
    fn a_new_text_has_a_transparent_colour() {
        let t = Text::new("A");
        assert_eq!(t.build(&font()).tiles[0].color, 0);
    }

    #[test]
    fn alignment_uses_the_widest_line_even_for_a_one_line_text() {
        let mut t = text("A\nAAA");
        t.multi_line = false;
        t.align = Align::Center;
        let b = t.build(&font());
        // widest 12 measured before the cut; "A" (4) centred: (12 - 4) / 2 = 4
        assert_eq!((b.width, b.tiles.len()), (12, 1));
        assert_eq!(b.tiles[0].dst[0], 4);
        t.align = Align::Right;
        assert_eq!(t.build(&font()).tiles[0].dst[0], 8);
    }

    #[test]
    fn padding_spacing_and_size() {
        let mut t = text("A\nA");
        t.multi_line = true;
        t.padding_x = 2;
        t.padding_y = 1;
        t.line_spacing = 3;
        let b = t.build(&font());
        // width 4 + 2*2, height 6*2 + 3 + 2*1
        assert_eq!((b.width, b.height), (8, 17));
        assert_eq!(b.tiles[0].dst, [2, 1, 3, 6]);
        assert_eq!(b.tiles[1].dst, [2, 1 + 6 + 3, 3, 6]);
    }

    #[test]
    fn backgrounds_come_first_and_a_rounded_one_cuts_its_corners() {
        let mut t = text("A");
        t.background = 0xFF112233;
        let b = t.build(&font());
        assert_eq!(b.tiles[0].kind, TileKind::Background);
        assert_eq!(b.tiles[0].dst, [0, 0, 4, 6]);
        t.rounded = true;
        let b = t.build(&font());
        assert_eq!(b.tiles.len(), 4);
        assert_eq!(b.tiles[0].dst, [1, 0, 3, 6]);
        assert_eq!(b.tiles[1].dst, [0, 1, 1, 4]);
        assert_eq!(b.tiles[2].dst, [4, 1, 1, 4]);
        assert_eq!(b.tiles[3].dst[0], 1); // the letter is shifted right by 1
        assert_eq!(b.width, 5);
    }

    #[test]
    fn an_empty_text_is_nothing() {
        let b = text("").build(&font());
        assert_eq!((b.tiles.len(), b.width, b.height), (0, 0, 0));
    }
}
