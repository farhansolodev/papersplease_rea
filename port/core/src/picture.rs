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
}
