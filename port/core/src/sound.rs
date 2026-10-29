//! The game's side of the volume settings (docs/audio.md, "The volume
//! settings"; docs/screens.md, part 4). The host's sound player does the
//! rest: it holds a category's volume to 0.0001..1 and plays it as
//! 20 x log10 decibels on the mixer (port/www/audio.js, as
//! `UnityPlatformAudio.setCategoryVolume`).

/// The two kinds of sound (`app.aud.AudioCategory`).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Category {
    Effect = 0,
    Music = 1,
}

/// A volume setting as the settings screen keeps it: tenths from 0 to 1.
pub fn setting(value: f64) -> f64 {
    if value.is_nan() {
        return 1.0;
    }
    ((value * 10.0).round() / 10.0).clamp(0.0, 1.0)
}

/// What `Game.applySettings` hands the audio layer for a setting: its
/// square, so 0.5 plays at 0.25 (-12 dB).
pub fn category_volume(setting: f64) -> f64 {
    setting * setting
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn settings_are_tenths_from_0_to_1() {
        assert_eq!(setting(0.54), 0.5);
        assert_eq!(setting(0.55), 0.6);
        assert_eq!(setting(1.7), 1.0);
        assert_eq!(setting(-0.2), 0.0);
        assert_eq!(setting(f64::NAN), 1.0);
    }

    #[test]
    fn the_volume_is_the_setting_squared() {
        assert_eq!(category_volume(1.0), 1.0);
        assert_eq!(category_volume(0.5), 0.25);
        assert_eq!(category_volume(0.0), 0.0);
        // 0.5 squared is -12 dB.
        assert!((20.0 * category_volume(0.5).log10() + 12.04).abs() < 0.01);
    }
}
