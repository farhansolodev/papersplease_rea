//! The game's general state machine (`app.Stater`, `app.State`) and the
//! curves its values move along (`app.Interp`), as read in full for
//! milestone 4a (docs/booth-screen.md, part 2). `fade.rs` keeps its own
//! copy of the same rules for the three screen-change states (milestone
//! 3b); new screens use this one. scripts/reference/boothscreen.py has the
//! same rules in Python.
//!
//! A state has functions run on entering, on every settled frame, at a time
//! in the state, and on leaving; targets (properties of its owner and the
//! values they go to); an interp time over which the targets blend from
//! where they were; and a duration after which it goes to a next state.
//!
//! - `go(name, instant)`: the current state's leave functions; then, unless
//!   instant (or there was no state), the new state's targets' present
//!   values are kept as the blend's start (the snapshot), the state is
//!   entered (its enter functions, its clock to 0, its targets at the
//!   start: blend 0) and the blend's countdown set to its interp time. An
//!   instant change, or a state with no interp time, puts the targets in
//!   place at once.
//! - `step(dt)`: while blending, the targets at t = 1 - countdown / interp
//!   time (at most 1); once t reaches 1 the blend is over and a state with
//!   duration 0 goes to its next state; otherwise the countdown loses dt
//!   (exactly 0 becomes -1). Once settled: a state with a duration and a
//!   next state goes there when its clock has reached the duration;
//!   otherwise its clock gains dt and its step and at-time functions run.

use std::f64::consts::PI;

use crate::num::lerp_scale;

/// A target's value: the game boxes numbers and true/false alike.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Value {
    Num(f64),
    Bool(bool),
}

/// How a target gets to its value (`app.Interp`; `Plain` is a value given
/// without one).
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum Curve {
    Plain,
    /// The start value before t, the target from t on.
    Step(f64),
    Linear,
    /// `BOUNCEBACK(perc, count)`: reaches the target, bounces back `count`
    /// times, each bounce smaller, and lands on it at the end.
    Bounceback(f64, i32),
}

/// `app.Interp.lerp`: numbers in a straight line; anything else jumps from
/// a to b at t = 0.5.
fn lerp(a: Value, b: Value, t: f64) -> Value {
    match (a, b) {
        (Value::Num(a), Value::Num(b)) => Value::Num((b - a) * t + a),
        _ if t < 0.5 => a,
        _ => b,
    }
}

impl Curve {
    /// `Interp.get(a, interp)` with this curve and target `b`.
    pub fn get(self, a: Value, b: Value, interp: f64) -> Value {
        let t = lerp_scale(interp, 0.0, 1.0, 0.0, 1.0);
        match self {
            Curve::Plain | Curve::Linear => lerp(a, b, t),
            Curve::Step(at) => {
                if t < at {
                    a
                } else {
                    b
                }
            }
            Curve::Bounceback(perc, count) => {
                let n1 = (count + 1) as f64;
                let half = count as f64 + 0.5;
                let k = (half * t + 0.5).floor();
                let first = 1.0 / n1;
                let kk = (k as i32) as f64 / n1;
                let amp = if first <= kk { (kk - first) * (0.0 - perc) + perc } else { 1.0 };
                let c = (half * PI * t).cos();
                lerp(a, b, 1.0 - c.abs() * amp)
            }
        }
    }
}

/// When a state's function runs.
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum When {
    Enter,
    Step,
    /// Once, on the first settled frame its clock has reached the time.
    AtStep(f64),
    Exit,
}

/// What the state machine works on: its owner's properties and functions.
pub trait Host<P, F> {
    fn get(&self, prop: P) -> Value;
    fn set(&mut self, prop: P, value: Value);
    fn run(&mut self, func: F);
}

struct Func<F> {
    when: When,
    func: F,
    done: bool,
}

pub struct State<P, F> {
    pub name: &'static str,
    interp: f64,
    duration: f64,
    after: Option<&'static str>,
    step_time: f64,
    funcs: Vec<Func<F>>,
    targets: Vec<(P, Value, Curve)>,
}

impl<P: Copy + PartialEq, F: Copy> State<P, F> {
    /// `setInterpDuration`.
    pub fn interp(&mut self, seconds: f64) -> &mut Self {
        self.interp = seconds;
        self
    }

    /// `setDuration(seconds, after)`.
    pub fn duration(&mut self, seconds: f64, after: &'static str) -> &mut Self {
        self.duration = seconds;
        self.after = Some(after);
        self
    }

    /// `addFunc`.
    pub fn func(&mut self, when: When, func: F) -> &mut Self {
        self.funcs.push(Func { when, func, done: false });
        self
    }

    /// One property of `addTarget`.
    pub fn target(&mut self, prop: P, value: Value, curve: Curve) -> &mut Self {
        self.targets.push((prop, value, curve));
        self
    }

    /// `State.apply`: each target at `interp` (none is 1) from its snapshot
    /// value (none: from the target itself).
    fn apply(&self, snapshot: Option<&[(P, Value)]>, interp: Option<f64>, host: &mut dyn Host<P, F>) {
        let t = interp.unwrap_or(1.0);
        for &(prop, b, curve) in &self.targets {
            let a = snapshot.and_then(|s| s.iter().find(|(p, _)| *p == prop)).map_or(b, |&(_, v)| v);
            host.set(prop, curve.get(a, b, t));
        }
    }

    fn snapshot(&self, host: &dyn Host<P, F>) -> Vec<(P, Value)> {
        self.targets.iter().map(|&(p, _, _)| (p, host.get(p))).collect()
    }
}

pub struct Stater<P, F> {
    states: Vec<State<P, F>>,
    cur: Option<usize>,
    snapshot: Option<Vec<(P, Value)>>,
    countdown: f64,
}

impl<P: Copy + PartialEq, F: Copy> Default for Stater<P, F> {
    fn default() -> Self {
        Self::new()
    }
}

impl<P: Copy + PartialEq, F: Copy> Stater<P, F> {
    pub fn new() -> Stater<P, F> {
        Stater { states: Vec::new(), cur: None, snapshot: None, countdown: 0.0 }
    }

    /// `addState`: no interp time, no duration.
    pub fn add(&mut self, name: &'static str) -> &mut State<P, F> {
        self.states.push(State {
            name,
            interp: 0.0,
            duration: -1.0,
            after: None,
            step_time: 0.0,
            funcs: Vec::new(),
            targets: Vec::new(),
        });
        self.states.last_mut().unwrap()
    }

    /// The current state's name ("" before the first `go`).
    pub fn current(&self) -> &'static str {
        self.cur.map_or("", |i| self.states[i].name)
    }

    /// The current state's clock (`get_stateTime`).
    pub fn state_time(&self) -> f64 {
        self.cur.map_or(0.0, |i| self.states[i].step_time)
    }

    pub fn is_blending(&self) -> bool {
        self.countdown != 0.0
    }

    fn run(&mut self, i: usize, when: fn(When) -> bool, host: &mut dyn Host<P, F>) {
        let funcs: Vec<F> = self.states[i].funcs.iter().filter(|f| when(f.when)).map(|f| f.func).collect();
        for f in funcs {
            host.run(f);
        }
    }

    /// `Stater.go`. An unknown name changes nothing (the game prints a
    /// trace).
    pub fn go(&mut self, name: &str, instant: bool, host: &mut dyn Host<P, F>) {
        let Some(new) = self.states.iter().position(|s| s.name == name) else { return };
        self.countdown = 0.0;
        let mut instant = instant;
        match self.cur {
            Some(old) => self.run(old, |w| w == When::Exit, host),
            None => instant = true,
        }
        if !instant {
            let snapshot = self.states[new].snapshot(host);
            self.cur = Some(new);
            self.enter(new, Some(&snapshot), host);
            self.snapshot = Some(snapshot);
            self.countdown = self.states[new].interp;
            if self.countdown == 0.0 {
                self.states[new].apply(None, None, host);
            }
        } else {
            self.cur = Some(new);
            self.enter(new, None, host);
            self.states[new].apply(None, None, host);
        }
        if self.countdown == 0.0 {
            self.states[new].apply(self.snapshot.as_deref(), Some(1.0), host);
        }
    }

    /// `State.enter`: the enter functions, the at-time functions made ready
    /// again, the clock to 0, the targets at the snapshot (blend 0) or in
    /// place.
    fn enter(&mut self, i: usize, snapshot: Option<&[(P, Value)]>, host: &mut dyn Host<P, F>) {
        self.run(i, |w| w == When::Enter, host);
        let s = &mut self.states[i];
        s.funcs.iter_mut().for_each(|f| f.done = false);
        s.step_time = 0.0;
        let t = if snapshot.is_some() { 0.0 } else { 1.0 };
        s.apply(snapshot, Some(t), host);
    }

    /// `Stater.step`, once a frame with its clock's time.
    pub fn step(&mut self, dt: f64, host: &mut dyn Host<P, F>) {
        let Some(i) = self.cur else { return };
        if self.countdown == 0.0 {
            let s = &self.states[i];
            match s.after {
                Some(after) if s.duration >= 0.0 && s.step_time >= s.duration => self.go(after, false, host),
                _ => self.state_step(i, dt, host),
            }
        } else {
            let s = &self.states[i];
            let t = 1.0 - self.countdown / s.interp;
            s.apply(self.snapshot.as_deref(), Some(f64::min(1.0, t)), host);
            if 1.0 <= t {
                self.countdown = 0.0;
                if let (0.0, Some(after)) = (s.duration, s.after) {
                    self.go(after, false, host);
                }
            } else {
                self.countdown -= dt;
                if self.countdown == 0.0 {
                    self.countdown = -1.0;
                }
            }
        }
    }

    /// `State.step`: the clock gains dt, then the step functions and the
    /// at-time functions whose time has come, in the order they were added.
    fn state_step(&mut self, i: usize, dt: f64, host: &mut dyn Host<P, F>) {
        let s = &mut self.states[i];
        s.step_time += dt;
        let mut due = Vec::new();
        for f in s.funcs.iter_mut() {
            match f.when {
                When::Step => due.push(f.func),
                When::AtStep(at) if !f.done && at <= s.step_time => {
                    f.done = true;
                    due.push(f.func);
                }
                _ => {}
            }
        }
        for f in due {
            host.run(f);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[derive(Debug, Clone, Copy, PartialEq)]
    enum P {
        Y,
        On,
    }

    #[derive(Default)]
    struct Owner {
        y: f64,
        on: bool,
        ran: Vec<&'static str>,
    }

    impl Host<P, &'static str> for Owner {
        fn get(&self, p: P) -> Value {
            match p {
                P::Y => Value::Num(self.y),
                P::On => Value::Bool(self.on),
            }
        }
        fn set(&mut self, p: P, v: Value) {
            match (p, v) {
                (P::Y, Value::Num(y)) => self.y = y,
                (P::On, Value::Bool(b)) => self.on = b,
                _ => panic!("wrong value for {p:?}"),
            }
        }
        fn run(&mut self, f: &'static str) {
            self.ran.push(f);
        }
    }

    #[test]
    fn bounceback_starts_and_ends_on_its_values_and_bounces_once() {
        let at = |t| match Curve::Bounceback(0.2, 1).get(Value::Num(0.0), Value::Num(100.0), t) {
            Value::Num(v) => v,
            _ => unreachable!(),
        };
        assert_eq!(at(0.0), 0.0);
        assert!((at(1.0 / 3.0) - 100.0).abs() < 1e-9, "the target first at a third");
        assert!((at(2.0 / 3.0) - 80.0).abs() < 1e-9, "back by 20% at the bounce's top");
        assert_eq!(at(1.0), 100.0);
    }

    #[test]
    fn a_blend_runs_over_its_interp_time_then_goes_on() {
        let mut s: Stater<P, &'static str> = Stater::new();
        s.add("off").func(When::Exit, "off-exit").target(P::Y, Value::Num(0.0), Curve::Plain);
        s.add("fall")
            .interp(0.5)
            .duration(0.0, "rest")
            .func(When::Enter, "fall-enter")
            .target(P::Y, Value::Num(30.0), Curve::Linear)
            .target(P::On, Value::Bool(false), Curve::Step(1.0));
        s.add("rest").func(When::AtStep(0.1), "rest-at");
        let mut o = Owner { on: true, ..Owner::default() };
        s.go("off", true, &mut o);
        s.go("fall", false, &mut o);
        assert_eq!(o.ran, ["off-exit", "fall-enter"]);
        assert_eq!((o.y, o.on), (0.0, true));
        let mut ys = Vec::new();
        for _ in 0..40 {
            s.step(1.0 / 60.0, &mut o);
            ys.push(o.y);
            if s.current() == "rest" {
                break;
            }
        }
        // t = 0 on the first step, then about 1/30 more each step. Thirty
        // subtractions of 1/60 leave the countdown a hair above 0, so t
        // reaches 1 on the 32nd step, not the 31st, and the state moves on.
        let mut countdown = 0.5_f64;
        let mut steps = 1;
        while 1.0 - countdown / 0.5 < 1.0 {
            countdown -= 1.0 / 60.0;
            steps += 1;
        }
        assert_eq!(ys[0], 0.0);
        assert_eq!(steps, 32);
        assert_eq!(ys.len(), steps);
        assert_eq!((o.y, o.on), (30.0, false));
        // Six steps of 1/60 add up to just under 0.1: the seventh runs it.
        for _ in 0..8 {
            s.step(1.0 / 60.0, &mut o);
        }
        assert_eq!(o.ran.last(), Some(&"rest-at"));
        assert_eq!(o.ran.iter().filter(|f| **f == "rest-at").count(), 1);
    }
}
