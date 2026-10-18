//! The start pack: many files in one (format in
//! scripts/build_assets/build_pack.py).

use std::collections::HashMap;

pub struct Pack {
    bytes: Vec<u8>,
    index: HashMap<String, (usize, usize)>,
}

fn u16_at(b: &[u8], p: usize) -> Result<usize, String> {
    b.get(p..p + 2)
        .map(|s| u16::from_le_bytes([s[0], s[1]]) as usize)
        .ok_or_else(|| "pack is cut short".to_string())
}

fn u32_at(b: &[u8], p: usize) -> Result<usize, String> {
    b.get(p..p + 4)
        .map(|s| u32::from_le_bytes([s[0], s[1], s[2], s[3]]) as usize)
        .ok_or_else(|| "pack is cut short".to_string())
}

impl Pack {
    pub fn parse(bytes: Vec<u8>) -> Result<Pack, String> {
        if bytes.get(0..4) != Some(b"PPK1") {
            return Err("not a pack (bad start)".into());
        }
        let count = u32_at(&bytes, 4)?;
        let mut p = 8;
        let mut entries = Vec::with_capacity(count);
        for _ in 0..count {
            let len = u16_at(&bytes, p)?;
            let name = bytes
                .get(p + 2..p + 2 + len)
                .ok_or("pack is cut short")?
                .to_vec();
            let name = String::from_utf8(name).map_err(|_| "bad name in pack")?;
            let offset = u32_at(&bytes, p + 2 + len)?;
            let size = u32_at(&bytes, p + 6 + len)?;
            entries.push((name, offset, size));
            p += 10 + len;
        }
        let mut index = HashMap::new();
        for (name, offset, size) in entries {
            let (start, end) = (p + offset, p + offset + size);
            if end > bytes.len() {
                return Err(format!("pack is cut short at {name}"));
            }
            index.insert(name, (start, end));
        }
        Ok(Pack { bytes, index })
    }

    pub fn get(&self, name: &str) -> Option<&[u8]> {
        self.index.get(name).map(|&(a, b)| &self.bytes[a..b])
    }

    /// Every file's name, sorted.
    pub fn names(&self) -> Vec<&str> {
        let mut names: Vec<&str> = self.index.keys().map(String::as_str).collect();
        names.sort();
        names
    }

    pub fn len(&self) -> usize {
        self.index.len()
    }

    pub fn is_empty(&self) -> bool {
        self.index.is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn make(files: &[(&str, &[u8])]) -> Vec<u8> {
        let mut head = b"PPK1".to_vec();
        head.extend((files.len() as u32).to_le_bytes());
        let (mut table, mut data, mut offset) = (Vec::new(), Vec::new(), 0u32);
        for (name, blob) in files {
            table.extend((name.len() as u16).to_le_bytes());
            table.extend(name.as_bytes());
            table.extend(offset.to_le_bytes());
            table.extend((blob.len() as u32).to_le_bytes());
            data.extend(*blob);
            offset += blob.len() as u32;
        }
        [head, table, data].concat()
    }

    #[test]
    fn reads_files_back() {
        let pack = Pack::parse(make(&[("a/b.txt", b"hello"), ("c", b""), ("d", b"xyz")])).unwrap();
        assert_eq!(pack.len(), 3);
        assert_eq!(pack.get("a/b.txt"), Some(&b"hello"[..]));
        assert_eq!(pack.get("c"), Some(&b""[..]));
        assert_eq!(pack.get("d"), Some(&b"xyz"[..]));
        assert_eq!(pack.get("missing"), None);
    }

    #[test]
    fn refuses_bad_or_cut_packs() {
        assert!(Pack::parse(b"nope".to_vec()).is_err());
        let good = make(&[("a", b"hello")]);
        assert!(Pack::parse(good[..good.len() - 1].to_vec()).is_err());
        assert!(Pack::parse(good[..6].to_vec()).is_err());
    }
}
