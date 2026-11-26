//! The papers' definitions (`Papers.xml`, docs/papers-xml-format.md) and
//! how one page is laid out (`data.Page.getInnerImageAndMarkPositions` and
//! `play.day.PaperInnerVisuals`, docs/page-layout.md), as
//! scripts/reference/pages.py does it. Since milestone 4c (the rulebook's
//! contents page). Also the rulebook's page mask (`Facts.xml`'s
//! `<rulebook>`, docs/facts-xml-format.md) and which pages a paper has
//! (`PaperNav`).
//!
//! Not here yet: fact pictures (`BoothEnv.getImage`), seals, a picture
//! mark's `scale`, the touch padding (phone and tablet only), the rule and
//! news renames of a fact id.

use std::collections::HashMap;

use crate::pages::Gallery;
use crate::picture::Picture;
use crate::text::{Align, Text};
use crate::xmlscan::{tags, Tag};

/// A `<sounds>` set: the sound ids a paper plays.
#[derive(Debug, Clone, Default, PartialEq)]
pub struct SoundSet {
    pub drag_start: Option<String>,
    pub drag_stop: Option<String>,
    pub drop: Option<String>,
    pub to_top: Option<String>,
    pub turn_page: Option<String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum MarkKind {
    /// A literal text, or `$fact`.
    Text(String),
    /// A picture file of `assets/papers/`, `BLANK:WxH`, or `$fact`.
    Image(String),
    /// A seal (`emblem`).
    Emblem(String),
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Flow {
    None,
    Down,
    Right,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Mark {
    pub kind: MarkKind,
    pub align: Align,
    pub flow: Flow,
    pub font: String,
    pub text_color: u32,
    pub back_color: u32,
    pub wrap: i32,
    pub flow_pad: i32,
    pub side: usize,
    pub link: Option<String>,
    pub pos: Option<(f64, f64)>,
    pub pos2: Option<(f64, f64)>,
    pub clip_height: i32,
}

impl Mark {
    /// `Mark.getFactId`: a text or picture's name without its `$`, or
    /// `Emblem/<id>` for a seal; none for a literal.
    pub fn fact_id(&self) -> Option<String> {
        match &self.kind {
            MarkKind::Text(t) | MarkKind::Image(t) => t.strip_prefix('$').map(str::to_string),
            MarkKind::Emblem(e) => Some(format!("Emblem/{e}")),
        }
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct Page {
    pub id: String,
    pub image: String,
    pub marks: Vec<Mark>,
}

#[derive(Debug, Clone, PartialEq)]
pub struct PaperDef {
    pub id: String,
    pub outer: Option<String>,
    pub dock: bool,
    /// The id of its `<sounds>` set (`paper` when not given).
    pub sounds: String,
    pub reveal: Option<String>,
    pub pages: Vec<Page>,
}

/// The mark attributes a paper and a page pass on to their marks.
const INHERITED: [&str; 11] =
    ["align", "flow", "font", "textcolor", "backcolor", "wrap", "flowpad", "side", "scale", "emblemrect", "inspectable"];

fn parse_color(text: &str) -> u32 {
    let hex = text.trim_start_matches("0x").trim_start_matches("0X");
    u32::from_str_radix(hex, 16).unwrap_or(0) | 0xFF00_0000
}

fn parse_point(text: &str) -> Option<(f64, f64)> {
    let mut it = text.split_whitespace().map(|v| v.parse::<f64>());
    match (it.next(), it.next()) {
        (Some(Ok(x)), Some(Ok(y))) => Some((x, y)),
        _ => None,
    }
}

fn mark_from(attrs: &HashMap<String, String>) -> Option<Mark> {
    let a = |k: &str| attrs.get(k).map(String::as_str);
    let kind = if let Some(t) = a("text") {
        MarkKind::Text(t.to_string())
    } else if let Some(i) = a("image") {
        MarkKind::Image(i.to_string())
    } else {
        MarkKind::Emblem(a("emblem")?.to_string())
    };
    let align = match a("align").unwrap_or("left").to_ascii_uppercase().as_str() {
        "CENTER" => Align::Center,
        "RIGHT" => Align::Right,
        _ => Align::Left,
    };
    let flow = match a("flow").unwrap_or("none").to_ascii_uppercase().as_str() {
        "DOWN" => Flow::Down,
        "RIGHT" => Flow::Right,
        _ => Flow::None,
    };
    let int = |k: &str| a(k).and_then(|v| v.trim().parse::<i32>().ok()).unwrap_or(0);
    Some(Mark {
        kind,
        align,
        flow,
        font: a("font").unwrap_or("regular").to_string(),
        text_color: a("textcolor").map(parse_color).unwrap_or(0),
        back_color: match a("backcolor") {
            None | Some("0") => 0,
            Some(c) => parse_color(c),
        },
        wrap: int("wrap"),
        flow_pad: int("flowpad"),
        side: int("side").max(0) as usize,
        link: a("link").map(str::to_string),
        pos: a("pos").and_then(parse_point),
        pos2: a("pos2").and_then(parse_point),
        clip_height: int("clipheight"),
    })
}

fn attr_map(tag: &Tag) -> HashMap<String, String> {
    tag.attrs.iter().cloned().collect()
}

/// Reads `Papers.xml`: the papers in file order and the sound sets by id.
/// The file is flat enough to read tag by tag: a `<page>` belongs to the
/// last `<paper>`, a `<mark>` to the last `<page>`.
pub fn read_papers(xml: &str) -> (Vec<PaperDef>, HashMap<String, SoundSet>) {
    let mut papers: Vec<PaperDef> = Vec::new();
    let mut sounds = HashMap::new();
    let mut paper_defaults: HashMap<String, String> = HashMap::new();
    let mut page_defaults: HashMap<String, String> = HashMap::new();
    for tag in tags(xml) {
        let attrs = attr_map(&tag);
        match tag.name.as_str() {
            "sounds" => {
                let get = |k: &str| attrs.get(k).cloned();
                let set = SoundSet {
                    drag_start: get("dragstart"),
                    drag_stop: get("dragstop"),
                    drop: get("drop"),
                    to_top: get("totop"),
                    turn_page: get("turnpage"),
                };
                sounds.insert(attrs.get("id").cloned().unwrap_or_default(), set);
            }
            "paper" => {
                paper_defaults = INHERITED.iter().filter_map(|k| attrs.get(*k).map(|v| (k.to_string(), v.clone()))).collect();
                papers.push(PaperDef {
                    id: attrs.get("id").cloned().unwrap_or_default(),
                    outer: attrs.get("outer").cloned(),
                    dock: attrs.get("dock").map(|v| v == "true").unwrap_or(false),
                    sounds: attrs.get("sounds").cloned().unwrap_or_else(|| "paper".into()),
                    reveal: attrs.get("reveal").cloned(),
                    pages: Vec::new(),
                });
            }
            "page" => {
                let Some(paper) = papers.last_mut() else { continue };
                let mut all = paper_defaults.clone();
                all.extend(attrs.clone());
                page_defaults = INHERITED.iter().filter_map(|k| all.get(*k).map(|v| (k.to_string(), v.clone()))).collect();
                paper.pages.push(Page {
                    id: attrs.get("id").cloned().unwrap_or_else(|| "none".into()),
                    image: attrs.get("image").cloned().unwrap_or_default(),
                    marks: Vec::new(),
                });
            }
            "mark" => {
                let Some(page) = papers.last_mut().and_then(|p| p.pages.last_mut()) else { continue };
                let mut all = page_defaults.clone();
                all.extend(attrs);
                if let Some(mark) = mark_from(&all) {
                    page.marks.push(mark);
                }
            }
            _ => {}
        }
    }
    (papers, sounds)
}

/// `Rules/PageMask` (the `BoothEnv` constructor): the `<rulebook>` pages
/// of `Facts.xml` whose rule is in force (a substring test on the day's
/// rules text, `Day/Rules`) or have none, and whose confiscation is the
/// day's or have none; each id followed by `-`.
pub fn rulebook_page_mask(facts_xml: &str, rules: &str, confiscation: &str) -> String {
    let mut out = String::new();
    let mut inside = false;
    for tag in tags(facts_xml) {
        match tag.name.as_str() {
            "rulebook" => inside = true,
            "page" if inside => {
                if let Some(rule) = tag.attr("rule") {
                    if !rule.is_empty() && !rules.contains(rule) {
                        continue;
                    }
                }
                if let Some(conf) = tag.attr("confiscation") {
                    if !conf.is_empty() && conf != confiscation {
                        continue;
                    }
                }
                out.push_str(tag.attr("id").unwrap_or(""));
                out.push('-');
            }
            _ if inside => break,
            _ => {}
        }
    }
    out
}

/// `PaperNav`: which pages a paper has, from its `PageMask` text (empty:
/// every page). A page exists when its id occurs in the mask (a substring
/// test). The transcript's page count is not modelled yet.
pub struct Nav<'a> {
    pub paper: &'a PaperDef,
    pub mask: String,
}

impl Nav<'_> {
    pub fn has_page(&self, index: usize) -> bool {
        if self.mask.is_empty() {
            return true;
        }
        index < self.paper.pages.len() && self.mask.contains(self.paper.pages[index].id.as_str())
    }

    pub fn has_page_from_id(&self, id: &str) -> bool {
        self.mask.is_empty() || self.mask.contains(id)
    }

    pub fn next_index(&self, index: usize) -> Option<usize> {
        (index + 1..self.paper.pages.len()).find(|&i| self.has_page(i))
    }

    pub fn prev_index(&self, index: usize) -> Option<usize> {
        (0..index).rev().find(|&i| self.has_page(i))
    }

    /// `getExistingPageId`: the first of the link's comma-separated ids the
    /// paper has.
    pub fn existing_page_id<'b>(&self, link: &'b str) -> Option<&'b str> {
        link.split(',').find(|part| self.has_page_from_id(part))
    }
}

/// The two marker colours: opaque black for side 0, opaque red for side 1.
fn marker_side(p: [u8; 4]) -> Option<usize> {
    match p {
        [0, 0, 0, 255] => Some(0),
        [255, 0, 0, 255] => Some(1),
        _ => None,
    }
}

/// `Page.getInnerImageAndMarkPositions` on a copy of the page picture: one
/// position per mark (its `pos`, a random point between `pos` and `pos2`,
/// or the next marker pixel of its side, scanning rows left to right);
/// every marker pixel is painted over with the pixel read before it.
/// `random` gives the draws for `pos2` (none on the rulebook).
pub fn mark_positions(page: &Page, picture: &mut Picture, random: &mut dyn FnMut() -> f64) -> Vec<(f64, f64)> {
    let mut positions = Vec::with_capacity(page.marks.len());
    let mut waiting: [Vec<usize>; 2] = [Vec::new(), Vec::new()];
    for (i, mark) in page.marks.iter().enumerate() {
        match (mark.pos, mark.pos2) {
            (None, _) => {
                positions.push((0.0, 0.0));
                if mark.side < 2 {
                    waiting[mark.side].push(i);
                }
            }
            (Some(p), None) => positions.push(p),
            (Some(p), Some(q)) => {
                let (rx, ry) = (random(), random());
                positions.push((((q.0 - p.0) * rx + p.0).floor(), ((q.1 - p.1) * ry + p.1).floor()));
            }
        }
    }
    let mut next = [0usize; 2];
    let mut previous = [0u8; 4];
    for y in 0..picture.height {
        for x in 0..picture.width {
            let pixel = picture.texel(x, y);
            if let Some(side) = marker_side(pixel) {
                if next[side] < waiting[side].len() {
                    positions[waiting[side][next[side]]] = (x as f64, y as f64);
                    next[side] += 1;
                }
                picture.set(x, y, previous);
            }
            previous = pixel;
        }
    }
    positions
}

/// What a laid-out mark is.
#[derive(Debug, Clone)]
pub enum Visual {
    /// A text in a font (by id).
    Text { text: Text, font: String },
    /// A literal picture of `assets/papers/` (by file name).
    Image(String),
}

/// One visual of a page, named `MARK#<index>`, in the page's coordinates.
#[derive(Debug, Clone)]
pub struct Placed {
    pub index: usize,
    pub visual: Visual,
    pub x: f64,
    pub y: f64,
    pub w: i32,
    pub h: i32,
    pub link: Option<String>,
}

/// `PaperInnerVisuals`: the visuals of one page, in mark order. The
/// fonts come from the gallery; `value_text(fact)` a fact's text
/// (`BoothEnv.getLocalizedText`); `image_size(file)` a literal picture's
/// size (none leaves the mark out). Fact pictures and seals are left out
/// (not needed yet).
pub fn layout(
    paper: &PaperDef,
    page_index: usize,
    positions: &[(f64, f64)],
    nav: &Nav,
    gallery: &Gallery,
    value_text: &dyn Fn(&str) -> String,
    image_size: &dyn Fn(&str) -> Option<(i32, i32)>,
    has_rulebook_tabs: bool,
) -> Result<Vec<Placed>, String> {
    let page = &paper.pages[page_index];
    let mut out = Vec::new();
    let (mut right, mut bottom) = (0.0f64, 0.0f64);
    for (index, mark) in page.marks.iter().enumerate() {
        let (px, py) = positions[index];
        match mark.link.as_deref() {
            Some("#next") => {
                if nav.next_index(page_index).is_none() {
                    continue;
                }
            }
            Some("#prev") => {
                if nav.prev_index(page_index).is_none() {
                    continue;
                }
            }
            Some(link) => {
                if nav.existing_page_id(link).is_none() {
                    continue;
                }
            }
            None => {}
        }
        let fact = mark.fact_id();
        let placed = match &mark.kind {
            MarkKind::Text(literal) => {
                let string = match &fact {
                    Some(f) => value_text(f),
                    None => literal.clone(),
                };
                if string.is_empty() {
                    continue;
                }
                let mut string = string.replace("\\n", "\n");
                let f = gallery.font(&mark.font).ok_or_else(|| format!("Font not found: {}", mark.font))?;
                let mut t = Text::new("");
                t.color = mark.text_color;
                t.align = mark.align;
                let (x, y) = match mark.flow {
                    Flow::Down => (px, mark.flow_pad as f64 + bottom),
                    Flow::Right => (mark.flow_pad as f64 + right, py + 1.0 - f.ascent as f64),
                    Flow::None => (px, py + 1.0 - f.ascent as f64),
                };
                if mark.link.is_none() {
                    if mark.back_color != 0 {
                        t.background = mark.back_color;
                        t.padding_x = 1;
                    }
                } else {
                    // A button: the box in the text colour, rounded, the
                    // letters in the back colour.
                    t.background = mark.text_color;
                    t.rounded = true;
                    t.color = mark.back_color;
                    t.padding_x = 1;
                    t.padding_y = 1;
                }
                if mark.wrap != 0 {
                    t.multi_line = true;
                    t.fixed_width = mark.wrap;
                }
                if let Some(rest) = string.strip_prefix('@') {
                    std::mem::swap(&mut t.background, &mut t.color);
                    string = rest.to_string();
                }
                t.text = string;
                let built = t.build(f);
                let x = match mark.align {
                    Align::Center => (x - built.width as f64 * 0.5).floor(),
                    Align::Right => (x - built.width as f64).floor(),
                    Align::Left => x,
                };
                right = x + built.width as f64;
                bottom = y + built.height as f64;
                Placed {
                    index,
                    visual: Visual::Text { text: t, font: mark.font.clone() },
                    x,
                    y,
                    w: built.width,
                    h: built.height,
                    link: mark.link.clone(),
                }
            }
            MarkKind::Image(name) => {
                if name.starts_with("RulesTab") && !has_rulebook_tabs {
                    continue;
                }
                if fact.is_some() {
                    continue; // fact pictures: not yet
                }
                let Some((w, h)) = image_size(name) else { continue };
                let (mut x, mut y) = (px, py);
                match mark.flow {
                    Flow::Down => y = mark.flow_pad as f64 + bottom,
                    Flow::Right => x = mark.flow_pad as f64 + right,
                    Flow::None => {}
                }
                let x = match mark.align {
                    Align::Center => (x - w as f64 * 0.5).floor(),
                    Align::Right => (x - w as f64).floor(),
                    Align::Left => x,
                };
                right = x + w as f64;
                bottom = y + h as f64;
                Placed { index, visual: Visual::Image(name.clone()), x, y, w, h, link: mark.link.clone() }
            }
            MarkKind::Emblem(_) => continue, // seals: not yet
        };
        out.push(placed);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    const PAPERS: &str = r##"<papers>
<sounds id="paper" dragstart="a" dragstop="b" drop="b" totop="c" turnpage="d"/>
<paper id="P" outer="O.png" font="f" textcolor="0x574848" dock="true">
  <page id="home" image="H.png" backcolor="0xe4e6bd">
    <mark text="One" link="one"/>
    <mark text="Two" link="two" side="1"/>
    <mark image="X.png" pos="5 6"/>
    <mark image="N.png" link="#next" pos="1 2"/>
  </page>
  <page id="one" image="H.png" wrap="90"><mark text="$Rule0"/></page>
  <page id="two" image="H.png"/>
</paper>
</papers>"##;

    #[test]
    fn papers_are_read_with_inherited_attributes() {
        let (papers, sounds) = read_papers(PAPERS);
        assert_eq!(sounds["paper"].to_top.as_deref(), Some("c"));
        let p = &papers[0];
        assert!(p.dock);
        assert_eq!(p.sounds, "paper");
        assert_eq!(p.pages.len(), 3);
        let m = &p.pages[0].marks[0];
        assert_eq!((m.text_color, m.back_color, m.font.as_str()), (0xFF57_4848, 0xFFE4_E6BD, "f"));
        assert_eq!(p.pages[0].marks[1].side, 1);
        assert_eq!(p.pages[0].marks[2].pos, Some((5.0, 6.0)));
        assert_eq!(p.pages[1].marks[0].wrap, 90);
        assert_eq!(p.pages[1].marks[0].back_color, 0); // not passed from page 0
        assert_eq!(p.pages[1].marks[0].fact_id().as_deref(), Some("Rule0"));
    }

    #[test]
    fn the_rulebook_mask_follows_the_rules_and_the_confiscation() {
        let facts = r#"<facts><rulebook><page id="home"/><page id="docs" rule="RuleNeedIdCard"/>
            <page id="confiscation" confiscation="Native"/><page id="last"/></rulebook>
            <locs><loc id="x" val="y"/></locs><page id="later"/></facts>"#;
        assert_eq!(rulebook_page_mask(facts, "RuleNeedPassport;", ""), "home-last-");
        assert_eq!(rulebook_page_mask(facts, "RuleNeedIdCard;", "Native"), "home-docs-confiscation-last-");
    }

    #[test]
    fn marker_pixels_place_marks_and_are_painted_over() {
        let (papers, _) = read_papers(PAPERS);
        let page = &papers[0].pages[0];
        let mut pic = Picture::filled(4, 2, [9, 9, 9, 255]);
        pic.set(1, 0, [0, 0, 0, 255]); // side 0: the first mark
        pic.set(0, 1, [255, 0, 0, 255]); // side 1: the second mark
        pic.set(3, 1, [0, 0, 0, 255]); // one more black pixel: painted over, unused
        let pos = mark_positions(page, &mut pic, &mut || 0.0);
        assert_eq!(pos, vec![(1.0, 0.0), (0.0, 1.0), (5.0, 6.0), (1.0, 2.0)]);
        assert_eq!(pic.texel(1, 0), [9, 9, 9, 255]);
        assert_eq!(pic.texel(0, 1), [9, 9, 9, 255]); // the last pixel of the row above
        assert_eq!(pic.texel(3, 1), [9, 9, 9, 255]);
    }

    #[test]
    fn nav_reads_the_mask_as_substrings() {
        let (papers, _) = read_papers(PAPERS);
        let nav = Nav { paper: &papers[0], mask: "home-two-".into() };
        assert!(nav.has_page(0) && !nav.has_page(1) && nav.has_page(2));
        assert_eq!(nav.next_index(0), Some(2));
        assert_eq!(nav.prev_index(2), Some(0));
        assert_eq!(nav.existing_page_id("one,two"), Some("two"));
        assert_eq!(nav.existing_page_id("one"), None);
    }
}
