//! Pictures: width x height pixels of red, green, blue, alpha bytes (straight
//! alpha, as the game stores them: docs/vis-basics.md, "Pictures in memory").

pub struct Picture {
    pub width: u32,
    pub height: u32,
    /// `width * height * 4` bytes, rows top to bottom.
    pub rgba: Vec<u8>,
}

impl Picture {
    /// The 1 x 1 opaque white picture (`Image.white1x1`) every plain
    /// rectangle is stretched from.
    pub fn white() -> Picture {
        Picture {
            width: 1,
            height: 1,
            rgba: vec![255, 255, 255, 255],
        }
    }

    /// Decodes a PNG of any colour type to red, green, blue, alpha bytes
    /// (a palette is expanded, a missing alpha is opaque, 16 bits cut to 8).
    pub fn from_png(bytes: &[u8]) -> Result<Picture, String> {
        let mut decoder = png::Decoder::new(std::io::Cursor::new(bytes));
        decoder.set_transformations(png::Transformations::EXPAND | png::Transformations::STRIP_16);
        let mut reader = decoder.read_info().map_err(|e| format!("png: {e}"))?;
        let size = reader
            .output_buffer_size()
            .ok_or("png: picture too large")?;
        let mut buf = vec![0u8; size];
        let info = reader.next_frame(&mut buf).map_err(|e| format!("png: {e}"))?;
        let (width, height) = (info.width, info.height);
        let pixels = (width * height) as usize;
        let src = &buf[..info.buffer_size()];
        let mut rgba = Vec::with_capacity(pixels * 4);
        match info.color_type {
            png::ColorType::Rgba => rgba.extend_from_slice(src),
            png::ColorType::Rgb => {
                for p in src.chunks_exact(3) {
                    rgba.extend_from_slice(&[p[0], p[1], p[2], 255]);
                }
            }
            png::ColorType::Grayscale => {
                for &g in src {
                    rgba.extend_from_slice(&[g, g, g, 255]);
                }
            }
            png::ColorType::GrayscaleAlpha => {
                for p in src.chunks_exact(2) {
                    rgba.extend_from_slice(&[p[0], p[0], p[0], p[1]]);
                }
            }
            png::ColorType::Indexed => return Err("png: palette not expanded".into()),
        }
        if rgba.len() != pixels * 4 {
            return Err("png: unexpected size".into());
        }
        Ok(Picture { width, height, rgba })
    }

    /// The pixel at (x, y), which must be inside the picture.
    pub fn texel(&self, x: u32, y: u32) -> [u8; 4] {
        let i = ((y * self.width + x) * 4) as usize;
        [self.rgba[i], self.rgba[i + 1], self.rgba[i + 2], self.rgba[i + 3]]
    }

    /// A new picture of one colour (red, green, blue, alpha).
    pub fn filled(width: u32, height: u32, rgba: [u8; 4]) -> Picture {
        Picture { width, height, rgba: rgba.repeat((width * height) as usize) }
    }

    pub fn set(&mut self, x: u32, y: u32, rgba: [u8; 4]) {
        let i = ((y * self.width + x) * 4) as usize;
        self.rgba[i..i + 4].copy_from_slice(&rgba);
    }

    /// `Image.fill` over a rectangle (x, y, width, height), written as it
    /// is, cut to the picture (docs/fact-pictures.md).
    pub fn fill_rect(&mut self, rect: [i32; 4], rgba: [u8; 4]) {
        let [x, y, w, h] = rect;
        for py in y.max(0)..(y + h).min(self.height as i32) {
            for px in x.max(0)..(x + w).min(self.width as i32) {
                self.set(px as u32, py as u32, rgba);
            }
        }
    }

    /// `Image.paste` of a whole picture with the mode `BLEND`, its position
    /// cut toward zero (docs/fact-pictures.md): each colour channel =
    /// (target x (255 - a) + source x a) / 255 in whole numbers, alpha the
    /// larger of the two.
    pub fn paste_blend(&mut self, src: &Picture, x: f64, y: f64) {
        let (dx, dy) = (x as i32, y as i32);
        for sy in 0..src.height as i32 {
            for sx in 0..src.width as i32 {
                let (tx, ty) = (dx + sx, dy + sy);
                if tx < 0 || ty < 0 || tx >= self.width as i32 || ty >= self.height as i32 {
                    continue;
                }
                let s = src.texel(sx as u32, sy as u32);
                let t = self.texel(tx as u32, ty as u32);
                let a = s[3] as u32;
                let mix = |i: usize| ((t[i] as u32 * (255 - a) + s[i] as u32 * a) / 255) as u8;
                self.set(tx as u32, ty as u32, [mix(0), mix(1), mix(2), t[3].max(s[3])]);
            }
        }
    }
}

impl Clone for Picture {
    fn clone(&self) -> Picture {
        Picture { width: self.width, height: self.height, rgba: self.rgba.clone() }
    }
}
