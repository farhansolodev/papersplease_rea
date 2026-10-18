//! A tiny reader for the flat XML the font files use: it lists every tag
//! with its attributes and nothing else (no nesting, no text). Comments,
//! `<?...?>` and closing tags are skipped. Attribute values have their
//! character references decoded (`&quot;`, `&#13;`, ...), as an XML reader
//! does.

pub struct Tag {
    pub name: String,
    pub attrs: Vec<(String, String)>,
}

impl Tag {
    pub fn attr(&self, name: &str) -> Option<&str> {
        self.attrs
            .iter()
            .find(|(n, _)| n == name)
            .map(|(_, v)| v.as_str())
    }
}

pub fn decode_entities(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut rest = s;
    while let Some(i) = rest.find('&') {
        out.push_str(&rest[..i]);
        rest = &rest[i..];
        let Some(end) = rest.find(';') else { break };
        let name = &rest[1..end];
        let decoded = match name {
            "quot" => Some('"'),
            "amp" => Some('&'),
            "lt" => Some('<'),
            "gt" => Some('>'),
            "apos" => Some('\''),
            _ => name.strip_prefix('#').and_then(|n| {
                let code = match n.strip_prefix(['x', 'X']) {
                    Some(hex) => u32::from_str_radix(hex, 16).ok(),
                    None => n.parse::<u32>().ok(),
                };
                code.and_then(char::from_u32)
            }),
        };
        match decoded {
            Some(c) => {
                out.push(c);
                rest = &rest[end + 1..];
            }
            None => {
                out.push('&');
                rest = &rest[1..];
            }
        }
    }
    out.push_str(rest);
    out
}

pub fn tags(xml: &str) -> Vec<Tag> {
    let bytes = xml.as_bytes();
    let mut out = Vec::new();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i] != b'<' {
            i += 1;
            continue;
        }
        if xml[i..].starts_with("<!--") {
            i = xml[i..].find("-->").map_or(bytes.len(), |e| i + e + 3);
            continue;
        }
        // Find the closing '>' outside quotes.
        let mut j = i + 1;
        let mut quote = 0u8;
        while j < bytes.len() {
            let b = bytes[j];
            if quote != 0 {
                if b == quote {
                    quote = 0;
                }
            } else if b == b'"' || b == b'\'' {
                quote = b;
            } else if b == b'>' {
                break;
            }
            j += 1;
        }
        let body = &xml[i + 1..j.min(bytes.len())];
        i = j + 1;
        if body.starts_with('/') || body.starts_with('?') || body.starts_with('!') {
            continue;
        }
        let body = body.trim_end_matches('/');
        let name_end = body
            .find(|c: char| c.is_whitespace())
            .unwrap_or(body.len());
        let mut tag = Tag {
            name: body[..name_end].to_string(),
            attrs: Vec::new(),
        };
        let mut rest = body[name_end..].trim_start();
        while let Some(eq) = rest.find('=') {
            let name = rest[..eq].trim().to_string();
            let after = rest[eq + 1..].trim_start();
            let Some(q) = after.chars().next().filter(|c| *c == '"' || *c == '\'') else {
                break;
            };
            let Some(close) = after[1..].find(q) else { break };
            tag.attrs
                .push((name, decode_entities(&after[1..1 + close])));
            rest = after[close + 2..].trim_start();
        }
        out.push(tag);
    }
    out
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reads_tags_and_attributes() {
        let xml = r#"<?xml version="1.0"?>
<font>
 <!-- <font id="gone"/> -->
 <page id="0" file="a b.png"/>
 <char letter="&gt;" id='62' other="x>y"/>
 <char letter="&#13;" id="13"/>
</font>"#;
        let t = tags(xml);
        let names: Vec<_> = t.iter().map(|t| t.name.as_str()).collect();
        assert_eq!(names, ["font", "page", "char", "char"]);
        assert_eq!(t[1].attr("file"), Some("a b.png"));
        assert_eq!(t[2].attr("letter"), Some(">"));
        assert_eq!(t[2].attr("other"), Some("x>y"));
        assert_eq!(t[3].attr("letter"), Some("\r"));
        assert_eq!(t[3].attr("missing"), None);
    }

    #[test]
    fn decodes_the_references_the_font_files_use() {
        assert_eq!(decode_entities("&quot;&amp;&lt;&gt;"), "\"&<>");
        assert_eq!(decode_entities("a&#10;b&#x41;c"), "a\nbAc");
        assert_eq!(decode_entities("a & b"), "a & b");
    }
}
