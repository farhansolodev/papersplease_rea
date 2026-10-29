//! The game's effects as it stores them: IMA ADPCM in FMOD's block layout
//! (docs/audio.md, "The ADPCM block layout"), and the effects pack that
//! holds them (scripts/build_assets/build_audio.py).
//!
//! Per channel a block is 36 bytes: the block's first sample (signed 16-bit),
//! the step index, one unused byte, then 32 bytes of 4-bit codes, low half of
//! each byte first. A stereo block has both headers first, then the codes in
//! turns of 4 bytes per channel. The header sample is the block's first
//! sample and 63 codes follow; the 64th code is never used.

use crate::pack::Pack;

const STEPS: [i32; 89] = [
    7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 50, 55, 60, 66, 73,
    80, 88, 97, 107, 118, 130, 143, 157, 173, 190, 209, 230, 253, 279, 307, 337, 371, 408, 449,
    494, 544, 598, 658, 724, 796, 876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 2272,
    2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358, 5894, 6484, 7132, 7845, 8630, 9493,
    10442, 11487, 12635, 13899, 15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767,
];
const INDEX: [i32; 8] = [-1, -1, -1, -1, 2, 4, 6, 8];

/// One decoded effect.
#[derive(Debug, Clone, PartialEq)]
pub struct Clip {
    /// The game's own name, as `Sounds.xml` asks for it (`stamp-down.wav`).
    pub name: String,
    pub channels: u16,
    /// Samples per second (44,100 or 22,050).
    pub rate: u32,
    /// The samples, channels interleaved (`frames() * channels` of them).
    pub samples: Vec<i16>,
}

impl Clip {
    /// Samples per channel.
    pub fn frames(&self) -> usize {
        self.samples.len() / self.channels.max(1) as usize
    }
}

/// Decodes `frames` samples per channel from ADPCM blocks. Returns the
/// samples interleaved, or an error when the data is too short.
pub fn decode(blocks: &[u8], channels: usize, frames: usize) -> Result<Vec<i16>, String> {
    if channels == 0 {
        return Err("no channels".into());
    }
    let block = 36 * channels;
    let count = frames.div_ceil(64);
    if blocks.len() < count * block {
        return Err(format!("{} bytes of ADPCM, {} needed", blocks.len(), count * block));
    }
    let mut out = vec![0i16; frames * channels];
    for (n, b) in blocks.chunks_exact(block).take(count).enumerate() {
        let first = n * 64;
        let here = (frames - first).min(64);
        for c in 0..channels {
            let mut predictor = i16::from_le_bytes([b[4 * c], b[4 * c + 1]]) as i32;
            let mut index = (b[4 * c + 2] as i32).clamp(0, 88);
            out[first * channels + c] = predictor as i16;
            for k in 1..here {
                // Code k - 1 of this channel: 4 bytes (8 codes) per turn,
                // the turns alternating by channel.
                let code_no = k - 1;
                let turn = code_no / 8;
                let byte = b[4 * channels + 4 * (turn * channels + c) + (code_no % 8) / 2];
                let code = if code_no % 2 == 0 { byte & 15 } else { byte >> 4 } as i32;
                let step = STEPS[index as usize];
                let mut diff = step >> 3;
                if code & 1 != 0 {
                    diff += step >> 2;
                }
                if code & 2 != 0 {
                    diff += step >> 1;
                }
                if code & 4 != 0 {
                    diff += step;
                }
                let next = if code & 8 != 0 { predictor - diff } else { predictor + diff };
                predictor = next.clamp(-32768, 32767);
                index = (index + INDEX[(code & 7) as usize]).clamp(0, 88);
                out[(first + k) * channels + c] = predictor as i16;
            }
        }
    }
    Ok(out)
}

/// Decodes one entry of the effects pack: channels u16, rate u32, samples
/// per channel u32 (little-endian), then the blocks.
pub fn decode_entry(name: &str, blob: &[u8]) -> Result<Clip, String> {
    let head = blob.get(..10).ok_or_else(|| format!("{name}: cut short"))?;
    let channels = u16::from_le_bytes([head[0], head[1]]);
    let rate = u32::from_le_bytes([head[2], head[3], head[4], head[5]]);
    let frames = u32::from_le_bytes([head[6], head[7], head[8], head[9]]) as usize;
    let samples = decode(&blob[10..], channels as usize, frames).map_err(|e| format!("{name}: {e}"))?;
    Ok(Clip { name: name.to_string(), channels, rate, samples })
}

/// Every effect in the effects pack, by name order.
pub fn read_effects(pack: &Pack) -> Result<Vec<Clip>, String> {
    let mut out = Vec::new();
    for name in pack.names() {
        let Some(short) = name.strip_prefix("effects/") else { continue };
        out.push(decode_entry(short, pack.get(name).unwrap_or_default())?);
    }
    Ok(out)
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A mono block: header sample 1000, index 0, then the given codes.
    fn mono_block(codes: &[u8]) -> Vec<u8> {
        let mut b = vec![0u8; 36];
        b[..2].copy_from_slice(&1000i16.to_le_bytes());
        for (i, &c) in codes.iter().enumerate() {
            b[4 + i / 2] |= if i % 2 == 0 { c } else { c << 4 };
        }
        b
    }

    #[test]
    fn the_header_sample_comes_first_then_63_codes() {
        // Code 7 at step 7: diff = 0 + 1 + 3 + 7 = 11 (7>>3=0, 7>>2=1, 7>>1=3, 7).
        let out = decode(&mono_block(&[7, 0]), 1, 3).unwrap();
        assert_eq!(out, [1000, 1011, 1011 + (STEPS[8] >> 3) as i16]);
    }

    #[test]
    fn the_64th_code_is_never_used() {
        let mut codes = [0u8; 64];
        codes[63] = 15;
        let a = decode(&mono_block(&codes), 1, 64).unwrap();
        let b = decode(&mono_block(&[0u8; 64]), 1, 64).unwrap();
        assert_eq!(a, b);
    }

    #[test]
    fn stereo_codes_come_in_turns_of_four_bytes() {
        let mut b = vec![0u8; 72];
        b[..2].copy_from_slice(&0i16.to_le_bytes());
        b[4..6].copy_from_slice(&100i16.to_le_bytes());
        // First code of the right channel: byte 8 + 4 = 12. Code 4: +step.
        b[12] = 4;
        let out = decode(&b, 2, 2).unwrap();
        assert_eq!(out, [0, 100, 0, 107]);
    }

    #[test]
    fn short_data_is_refused() {
        assert!(decode(&[0u8; 35], 1, 1).is_err());
        assert!(decode(&[0u8; 36], 1, 65).is_err());
        assert!(decode(&[0u8; 36], 0, 1).is_err());
    }
}
