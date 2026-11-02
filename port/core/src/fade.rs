//! The game's own states for changing screens (`Game.createStater`, run by
//! `app.Stater` and `app.State`; docs/save-format.md part 2, "Queueing a
//! screen") and the fade cover they move (`ScreenFlash.fadeT`, docs/screens.md
//! part 11). Only the three states a screen change uses are here: `on`,
//! `off` and `off-instant` (`paused` and `flashing-to-title` come with the
//! screens that need them).
//!
//! How `app.Stater` runs a state, as read for this step:
//!
//! - `go`: the old state's exit functions run; the new state is entered (its
//!   enter functions run, its own clock starts at 0) and, unless the change
//!   is instant, the fade value at that moment is kept as the start of a
//!   blend towards the new state's target over its "interp" time.
//! - each step while blending: the value is start + (target - start) x t,
//!   with t = 1 - countdown / interp time (so the first step after `go`
//!   still shows the start value); the countdown goes down by the step's
//!   time; once t reaches 1 the state is settled. A state's own clock does
//!   not run while it blends.
//! - each step once settled: a state with a duration and a next state goes
//!   to it when its clock has reached the duration; otherwise its clock
//!   moves on.
//!
//! The fade value is kept as a 4-byte float, as the cover's colour holds it.

/// `kFadeDuration` (0.25) halved: each way of a fade.
pub const FADE_TIME: f64 = 0.125;
/// How long `off` holds the black screen before the change.
pub const OFF_TIME: f64 = 1.0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum State {
    On,
    Off,
    OffInstant,
}

/// What a state change asks of the game, in order.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Event {
    /// `off`'s enter function: the current screen loses its switches 4 and
    /// 16 (no input, no update; it is still drawn).
    FreezeScreen,
    /// `off`'s exit function: `applyScreenChange` with the pending change.
    ApplyScreenChange,
}

pub struct Fader {
    state: State,
    /// `on`'s interp time: `off`'s exit sets it back to the fade, and
    /// `off-instant`'s exit to 0.
    on_interp: f64,
    interp_countdown: f64,
    /// The state's own clock (`stepTime`).
    step_time: f64,
    /// The fade value when the state was entered (`transitionSnapshot`).
    snapshot: f64,
    fade: f32,
}

impl Default for Fader {
    fn default() -> Self {
        Self::new()
    }
}

impl Fader {
    /// Running (`on`), nothing covered.
    pub fn new() -> Fader {
        Fader { state: State::On, on_interp: FADE_TIME, interp_countdown: 0.0, step_time: 0.0, snapshot: 0.0, fade: 0.0 }
    }

    pub fn state(&self) -> State {
        self.state
    }

    /// The fade cover's alpha (0 hides it).
    pub fn fade(&self) -> f32 {
        self.fade
    }

    fn interp(&self, s: State) -> f64 {
        match s {
            State::On => self.on_interp,
            State::Off => FADE_TIME,
            State::OffInstant => 0.0,
        }
    }

    fn target(s: State) -> f64 {
        match s {
            State::On => 0.0,
            State::Off | State::OffInstant => 1.0,
        }
    }

    /// (duration, next state) of the states that have them.
    fn duration(s: State) -> Option<(f64, State)> {
        match s {
            State::On => None,
            State::Off => Some((OFF_TIME, State::On)),
            State::OffInstant => Some((0.0, State::On)),
        }
    }

    /// `State.apply` with a blend position `t`; `None` is "no start kept",
    /// which puts the target straight in.
    fn apply(&mut self, from: Option<f64>, t: f64) {
        let target = Self::target(self.state);
        let from = from.unwrap_or(target);
        self.fade = ((target - from) * t + from) as f32;
    }

    /// `Stater.go`.
    pub fn go(&mut self, to: State, instant: bool) -> Vec<Event> {
        let mut events = Vec::new();
        self.interp_countdown = 0.0;
        match self.state {
            State::Off => {
                self.on_interp = FADE_TIME;
                events.push(Event::ApplyScreenChange);
            }
            State::OffInstant => {
                self.on_interp = 0.0;
                events.push(Event::ApplyScreenChange);
            }
            State::On => {}
        }
        let snapshot = self.fade as f64;
        self.state = to;
        if to != State::On {
            events.push(Event::FreezeScreen);
        }
        self.step_time = 0.0;
        if instant {
            self.apply(None, 1.0);
            self.apply(None, 1.0);
        } else {
            self.snapshot = snapshot;
            self.apply(Some(snapshot), 0.0);
            self.interp_countdown = self.interp(to);
            if self.interp_countdown == 0.0 {
                self.apply(None, 1.0);
            }
        }
        // A state with neither a duration nor a blend is settled at once.
        if Self::duration(to).is_none() && self.interp_countdown == 0.0 {
            self.apply(Some(self.snapshot), 1.0);
        }
        events
    }

    /// `Stater.step`, once a frame with the frame's time.
    pub fn step(&mut self, dt: f64) -> Vec<Event> {
        if self.interp_countdown == 0.0 {
            if let Some((duration, next)) = Self::duration(self.state) {
                if duration >= 0.0 && self.step_time >= duration {
                    return self.go(next, false);
                }
            }
            self.step_time += dt;
        } else {
            let t = 1.0 - self.interp_countdown / self.interp(self.state);
            self.apply(Some(self.snapshot), f64::min(1.0, t));
            if t >= 1.0 {
                self.interp_countdown = 0.0;
                if let Some((0.0, next)) = Self::duration(self.state) {
                    return self.go(next, false);
                }
            } else {
                self.interp_countdown -= dt;
                if self.interp_countdown == 0.0 {
                    self.interp_countdown = -1.0;
                }
            }
        }
        Vec::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const DT: f64 = 1.0 / 60.0;

    #[test]
    fn a_screen_change_fades_out_waits_a_second_and_fades_in() {
        let mut f = Fader::new();
        // The click: `off` is entered, the screen frozen, nothing covered yet.
        assert_eq!(f.go(State::Off, false), [Event::FreezeScreen]);
        assert_eq!(f.fade(), 0.0);
        let mut fades = Vec::new();
        let mut change_at = None;
        for frame in 1..200 {
            let events = f.step(DT);
            if events.contains(&Event::ApplyScreenChange) {
                change_at = Some(frame);
                assert_eq!(f.state(), State::On);
                assert_eq!(f.fade(), 1.0, "the new screen is built under a black cover");
            }
            fades.push(f.fade());
        }
        // Fading out: 0, 2/15, 4/15 ... 14/15, then black from the 9th step.
        assert_eq!(fades[0], 0.0);
        assert_eq!(fades[1], (1.0 - (FADE_TIME - DT) / FADE_TIME) as f32);
        assert!(fades[7] < 1.0);
        assert_eq!(fades[8], 1.0);
        // The second's wait starts on the step after: steps 10 to 69 add up
        // 60 x 1/60 s, which reaches 1.0, so the change comes on step 70
        // (1.17 s after the click)...
        let change = change_at.expect("the change was applied");
        assert_eq!(change, 70, "the change after {change} steps");
        // ...and the cover is gone 10 steps later.
        assert_eq!(fades[change - 1 + 9], 0.0);
        assert!(fades[change - 1 + 8] > 0.0);
        assert!(fades[change..].windows(2).all(|p| p[1] <= p[0]));
    }

    #[test]
    fn an_instant_change_has_no_fade_either_way() {
        let mut f = Fader::new();
        assert_eq!(f.go(State::OffInstant, true), [Event::FreezeScreen]);
        assert_eq!(f.fade(), 1.0);
        assert_eq!(f.step(DT), [Event::ApplyScreenChange]);
        assert_eq!(f.fade(), 0.0, "on's blend time is 0 after an instant change");
    }
}
