//! Decodes every effect of the effects pack and compares it with the WAV
//! files FMOD made (docs/audio.md), sample for sample (milestone 2). Needs two
//! gitignored, game-derived inputs; with either missing the test says so and
//! passes without checking:
//!
//!     python -I scripts/build_assets/build_audio.py      -> build/assets/effects.pack
//!     .venv\Scripts\python -I scripts/unity/audio_extract.py game\PapersPlease_Data extracted\audio

use std::path::{Path, PathBuf};

use pp_core::adpcm;
use pp_core::pack::Pack;

fn root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}

/// Channels, rate and samples of a 16-bit PCM WAV with the plain 44-byte
/// header audio_extract.py writes.
fn read_wav(bytes: &[u8]) -> (u16, u32, Vec<i16>) {
    assert_eq!(&bytes[0..4], b"RIFF");
    assert_eq!(&bytes[36..40], b"data");
    let channels = u16::from_le_bytes([bytes[22], bytes[23]]);
    let rate = u32::from_le_bytes([bytes[24], bytes[25], bytes[26], bytes[27]]);
    let samples = bytes[44..].chunks_exact(2).map(|s| i16::from_le_bytes([s[0], s[1]])).collect();
    (channels, rate, samples)
}

#[test]
fn every_effect_matches_fmods_decode() {
    let pack_path = root().join("build/assets/effects.pack");
    let wavs = root().join("extracted/audio");
    let Ok(bytes) = std::fs::read(&pack_path) else {
        eprintln!("SKIPPED: {} not found", pack_path.display());
        return;
    };
    if !wavs.is_dir() {
        eprintln!("SKIPPED: {} not found", wavs.display());
        return;
    }
    let clips = adpcm::read_effects(&Pack::parse(bytes).unwrap()).unwrap();
    assert_eq!(clips.len(), 108);
    let mut differing = Vec::new();
    for clip in &clips {
        let wav = std::fs::read(wavs.join(&clip.name)).unwrap();
        let (channels, rate, samples) = read_wav(&wav);
        if (channels, rate) != (clip.channels, clip.rate) || samples != clip.samples {
            differing.push(clip.name.clone());
        }
    }
    assert!(differing.is_empty(), "differ from the WAV files: {differing:?}");
    eprintln!("all 108 effects are identical to FMOD's decode");
}
