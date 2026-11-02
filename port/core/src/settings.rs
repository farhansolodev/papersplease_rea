//! The player's settings (`play.Settings`, docs/screens.md part 4, "Who
//! writes the settings file", and docs/save-format.md, "Settings"): each
//! setter stores a changed value and adds 1 to the change counter; nothing
//! here writes anything. `Game` applies and saves on the frame a change is
//! seen.
//!
//! Left out of the port: the language code (English only, the user's
//! decision), vibration (no desktop row), the endless choice and unlock
//! (later milestones).

/// `play.Settings`' three date formats: (short, long, the example the
/// settings row shows).
pub const DATE_FORMATS: [(&str, &str, &str); 3] = [
    ("%y.%m.%d", "%Y.%m.%d", "1982-1-23"),
    ("%d.%m.%y", "%d.%m.%Y", "23-1-1982"),
    ("%m.%d.%y", "%m.%d.%Y", "1-23-1982"),
];

/// The values a settings file can hold, as the host stores them.
#[derive(Debug, Clone, Copy, PartialEq)]
pub struct Saved {
    pub fullscreen: bool,
    pub nudity: bool,
    pub easy_mode: bool,
    pub date_format_index: i32,
    pub music_volume: f64,
    pub sound_volume: f64,
}

#[derive(Debug, Clone)]
pub struct Settings {
    fullscreen: bool,
    nudity: bool,
    easy_mode: bool,
    date_format_index: i32,
    music_volume: f64,
    sound_volume: f64,
    /// Changes since the start; starts at 1.
    generation: u32,
    generation_at_load: u32,
}

impl Settings {
    /// The constructor: both volumes 1.0, nudity as the platform's default
    /// (on for desktop), then the saved values if there are any (each
    /// through its setter; a load adds 1 to the counter and remembers it).
    pub fn new(default_nudity: bool, saved: Option<&Saved>) -> Settings {
        let mut s = Settings {
            fullscreen: false,
            nudity: default_nudity,
            easy_mode: false,
            date_format_index: 0,
            music_volume: 1.0,
            sound_volume: 1.0,
            generation: 1,
            generation_at_load: 0,
        };
        if let Some(saved) = saved {
            let before = s.generation;
            s.set_fullscreen(saved.fullscreen);
            s.set_nudity(saved.nudity);
            s.set_music_volume(saved.music_volume);
            s.set_sound_volume(saved.sound_volume);
            s.set_easy_mode(saved.easy_mode);
            s.set_date_format_index(saved.date_format_index);
            s.generation = before + 1;
            s.generation_at_load = s.generation;
        }
        s
    }

    pub fn generation(&self) -> u32 {
        self.generation
    }

    pub fn fullscreen(&self) -> bool {
        self.fullscreen
    }
    pub fn nudity(&self) -> bool {
        self.nudity
    }
    pub fn easy_mode(&self) -> bool {
        self.easy_mode
    }
    pub fn date_format_index(&self) -> i32 {
        self.date_format_index
    }
    pub fn music_volume(&self) -> f64 {
        self.music_volume
    }
    pub fn sound_volume(&self) -> f64 {
        self.sound_volume
    }

    fn changed(&mut self) {
        self.generation = self.generation.wrapping_add(1);
    }

    pub fn set_fullscreen(&mut self, v: bool) {
        if v != self.fullscreen {
            self.changed();
            self.fullscreen = v;
        }
    }
    pub fn set_nudity(&mut self, v: bool) {
        if v != self.nudity {
            self.changed();
            self.nudity = v;
        }
    }
    pub fn set_easy_mode(&mut self, v: bool) {
        if v != self.easy_mode {
            self.changed();
            self.easy_mode = v;
        }
    }
    /// Kept within the list of formats.
    pub fn set_date_format_index(&mut self, v: i32) {
        if v != self.date_format_index {
            self.changed();
            self.date_format_index = v.clamp(0, DATE_FORMATS.len() as i32 - 1);
        }
    }
    pub fn set_music_volume(&mut self, v: f64) {
        if v != self.music_volume {
            self.changed();
            self.music_volume = v;
        }
    }
    pub fn set_sound_volume(&mut self, v: f64) {
        if v != self.sound_volume {
            self.changed();
            self.sound_volume = v;
        }
    }

    /// What a save writes.
    pub fn saved(&self) -> Saved {
        Saved {
            fullscreen: self.fullscreen,
            nudity: self.nudity,
            easy_mode: self.easy_mode,
            date_format_index: self.date_format_index,
            music_volume: self.music_volume,
            sound_volume: self.sound_volume,
        }
    }

    /// `Settings.save`: the values to write, or `None` when nothing changed
    /// since the load.
    pub fn save(&self) -> Option<Saved> {
        (self.generation != self.generation_at_load).then(|| self.saved())
    }
}

/// `musicButton_whenClick` and the others: the volume rounded to the
/// nearest tenth, moved by 0.1 and kept within 0 to 1.
pub fn volume_step(v: f64, up: bool) -> f64 {
    let tenths = crate::num::math_round(v * 10.0) as f64 / 10.0;
    if up {
        f64::min(1.0, tenths + 0.1)
    } else {
        f64::max(0.0, tenths - 0.1)
    }
}

/// `musicButton_whenClickVolumeBar`: a place along the bar (0 to 1, or
/// beyond while the pointer is held outside) to a volume in tenths.
pub fn volume_from_bar(v: f64) -> f64 {
    f64::min(1.0, f64::max(0.0, crate::num::math_round(v * 10.0) as f64 / 10.0))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_setter_counts_a_change_only_when_the_value_changes() {
        let mut s = Settings::new(true, None);
        assert_eq!(s.generation(), 1);
        s.set_nudity(true);
        assert_eq!(s.generation(), 1);
        s.set_nudity(false);
        s.set_music_volume(0.5);
        assert_eq!(s.generation(), 3);
        s.set_date_format_index(7);
        assert_eq!(s.date_format_index(), 2, "kept within the three formats");
    }

    #[test]
    fn a_load_counts_once_and_is_not_saved_again() {
        let saved = Saved {
            fullscreen: true,
            nudity: false,
            easy_mode: true,
            date_format_index: 1,
            music_volume: 0.3,
            sound_volume: 0.7,
        };
        let mut s = Settings::new(true, Some(&saved));
        assert_eq!(s.generation(), 2);
        assert_eq!(s.save(), None);
        assert_eq!(s.saved(), saved);
        s.set_easy_mode(false);
        assert!(s.save().is_some());
        // Nothing saved yet: the defaults are written on the first apply.
        assert!(Settings::new(true, None).save().is_some());
    }

    #[test]
    fn volume_steps_are_tenths_from_0_to_1() {
        assert_eq!(volume_step(1.0, true), 1.0);
        assert_eq!(volume_step(0.3, false), 0.19999999999999998);
        assert_eq!(volume_step(0.0, false), 0.0);
        assert_eq!(volume_step(0.04, true), 0.1);
        assert_eq!(volume_from_bar(-0.3), 0.0);
        assert_eq!(volume_from_bar(0.46), 0.5);
        assert_eq!(volume_from_bar(1.7), 1.0);
    }
}
