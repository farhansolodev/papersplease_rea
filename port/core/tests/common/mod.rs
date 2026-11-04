//! What the frame-by-frame tests share.

#![allow(dead_code)]

/// A small reader for the reference's timeline.json, which holds only
/// numbers, strings, true/false/null, lists and objects.
#[derive(Debug, Clone, PartialEq)]
pub enum Json {
    Null,
    Bool(bool),
    Num(f64),
    Str(String),
    List(Vec<Json>),
    Obj(Vec<(String, Json)>),
}

impl Json {
    pub fn parse(s: &str) -> Json {
        let mut chars = s.chars().peekable();
        Json::value(&mut chars)
    }

    fn value(c: &mut std::iter::Peekable<std::str::Chars>) -> Json {
        while c.peek().is_some_and(|x| x.is_whitespace()) {
            c.next();
        }
        match c.peek().copied() {
            Some('{') => {
                c.next();
                let mut out = Vec::new();
                loop {
                    match Json::value(c) {
                        Json::Str(k) => {
                            while c.next() != Some(':') {}
                            out.push((k, Json::value(c)));
                        }
                        _ => return Json::Obj(out),
                    }
                    while let Some(x) = c.next() {
                        if x == ',' {
                            break;
                        }
                        if x == '}' {
                            return Json::Obj(out);
                        }
                    }
                }
            }
            Some('[') => {
                c.next();
                let mut out = Vec::new();
                loop {
                    while c.peek().is_some_and(|x| x.is_whitespace()) {
                        c.next();
                    }
                    if c.peek() == Some(&']') {
                        c.next();
                        return Json::List(out);
                    }
                    out.push(Json::value(c));
                    while let Some(x) = c.next() {
                        if x == ',' {
                            break;
                        }
                        if x == ']' {
                            return Json::List(out);
                        }
                    }
                }
            }
            Some('"') => {
                c.next();
                let mut s = String::new();
                while let Some(x) = c.next() {
                    match x {
                        '"' => break,
                        '\\' => s.push(c.next().unwrap()),
                        x => s.push(x),
                    }
                }
                Json::Str(s)
            }
            Some('}') | Some(']') | None => Json::Null,
            Some(_) => {
                let mut word = String::new();
                while c.peek().is_some_and(|x| !",]} \n\r\t".contains(*x)) {
                    word.push(c.next().unwrap());
                }
                match word.as_str() {
                    "null" => Json::Null,
                    "true" => Json::Bool(true),
                    "false" => Json::Bool(false),
                    n => Json::Num(n.parse().unwrap()),
                }
            }
        }
    }

    pub fn get(&self, key: &str) -> &Json {
        match self {
            Json::Obj(items) => &items.iter().find(|(k, _)| k == key).unwrap_or_else(|| panic!("no {key}")).1,
            _ => panic!("not an object"),
        }
    }

    pub fn list(&self) -> &[Json] {
        match self {
            Json::List(l) => l,
            _ => panic!("not a list"),
        }
    }

    pub fn num(&self) -> Option<i64> {
        match self {
            Json::Num(n) => Some(*n as i64),
            _ => None,
        }
    }

    pub fn str(&self) -> &str {
        match self {
            Json::Str(s) => s,
            _ => panic!("not a string"),
        }
    }

    /// The number as a float (`num` cuts it to a whole number).
    pub fn float(&self) -> f64 {
        match self {
            Json::Num(n) => *n,
            _ => panic!("not a number"),
        }
    }
}
