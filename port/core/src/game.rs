//! The game: the current screen, the change from one screen to another and
//! the settings (`Game`, docs/save-format.md part 2 and docs/screens.md part
//! 4). One [`Game::step`] is one frame of `Game.update`, in its order:
//!
//! 1. the input (the host's frame, before `Game.update`);
//! 2. the clock, then the screen-change states ([`Fader`]), which may build
//!    the next screen;
//! 3. the screen's update, unless it is frozen by a change;
//! 4. the music;
//! 5. the screen's input, unless frozen (a click may ask for another
//!    screen);
//! 6. the speaker;
//! 7. the settings: applied and saved on the frame their change counter
//!    has moved; otherwise the window's full screen is copied into them if
//!    it differs.
//!
//! The pause key is not looked at yet: the intro screen (milestone 3c) is
//! the first screen built that can be paused, and the pause comes in 3d.

use crate::aud::{AudioHost, Music, SoundDefs, Speaker};
use crate::day::{self, DayScreen};
use crate::fade::{Event, Fader, State};
use crate::input::{self, HostInput, Input};
use crate::intro::{self, IntroScreen};
use crate::pages::Gallery;
use crate::raster::Screen;
use crate::settings::{Saved, Settings};
use crate::settings_screen::{self, SettingsScreen};
use crate::sound::{category_volume, Category};
use crate::title::{self, TitleScreen};

/// What the game asks of the platform besides sound (`PlatformSys`,
/// `EncryptedStore`): the window's full screen and keeping the settings.
pub trait Platform {
    fn fullscreen(&mut self) -> bool;
    fn set_fullscreen(&mut self, on: bool);
    fn save_settings(&mut self, saved: &Saved);
}

pub enum GameScreen {
    /// Before the first screen of a run that starts elsewhere than the
    /// title (the test address `?page=intro`): black.
    Empty,
    Title(TitleScreen),
    Settings(SettingsScreen),
    Intro(Box<IntroScreen>),
    /// The day screen at the start of day 1 (milestone 4a).
    Day(Box<DayScreen>),
}

pub struct Game {
    pub input: Input,
    pub speaker: Speaker,
    pub music: Music,
    pub settings: Settings,
    /// The settings' change counter when they were last applied (0 at the
    /// start, so the first frame applies them).
    settings_generation: u32,
    fader: Fader,
    screen: GameScreen,
    /// The screen's switches 4 and 16 cleared: no input, no update.
    frozen: bool,
    pending: Option<&'static str>,
    /// The game's clock (`app.Clock.time`) and this frame's time.
    time: f64,
    dt: f64,
    /// Lines for the host's log (clicks that lead nowhere yet).
    pub log: Vec<String>,
}

impl Game {
    /// The start: the first title screen of the run (the one that rises)
    /// and its song.
    pub fn new(gallery: &Gallery, defs: SoundDefs, settings: Settings, audio: &mut dyn AudioHost) -> Result<Game, String> {
        let mut game = Game::blank(defs, settings);
        game.screen = GameScreen::Title(TitleScreen::new(gallery, true)?);
        game.music.play(Some(title::SONG), &mut game.speaker, audio);
        Ok(game)
    }

    /// A start on the intro, for the test address `?page=intro` (the
    /// original reaches it from the load screen, which comes in milestone
    /// 6): an instant change to the intro is queued, so the first frame
    /// builds it as a screen change does, with that frame's time.
    pub fn new_intro(defs: SoundDefs, settings: Settings) -> Game {
        Game::new_on("intro", defs, settings)
    }

    /// A start on day 1's screen, for the test address `?page=day` (the
    /// original reaches it from the day-1 newspaper, which comes in
    /// milestone 6), built as `new_intro` builds the intro.
    pub fn new_day(defs: SoundDefs, settings: Settings) -> Game {
        Game::new_on("day", defs, settings)
    }

    fn new_on(screen: &'static str, defs: SoundDefs, settings: Settings) -> Game {
        let mut game = Game::blank(defs, settings);
        game.pending = Some(screen);
        for event in game.fader.go(State::OffInstant, true) {
            if event == Event::FreezeScreen {
                game.frozen = true;
            }
        }
        game
    }

    fn blank(defs: SoundDefs, settings: Settings) -> Game {
        Game {
            input: Input::new(),
            speaker: Speaker::new(defs),
            music: Music::new(),
            settings,
            settings_generation: 0,
            fader: Fader::new(),
            screen: GameScreen::Empty,
            frozen: false,
            pending: None,
            time: 0.0,
            dt: 0.0,
            log: Vec::new(),
        }
    }

    pub fn screen(&self) -> &GameScreen {
        &self.screen
    }

    /// The fade cover's alpha.
    pub fn fade(&self) -> f32 {
        self.fader.fade()
    }

    /// The state of the screen change (`on` while a screen runs).
    pub fn change_state(&self) -> State {
        self.fader.state()
    }

    /// One frame of `dt` seconds.
    pub fn step(&mut self, host: &HostInput, dt: f64, gallery: &mut Gallery, audio: &mut dyn AudioHost, platform: &mut dyn Platform) -> Result<(), String> {
        self.input.update(host, dt);
        self.time += dt;
        self.dt = dt;
        for event in self.fader.step(dt) {
            self.handle(event, gallery, audio)?;
        }
        if !self.frozen {
            match &mut self.screen {
                GameScreen::Empty => {}
                GameScreen::Title(t) => t.update(&self.music, &self.speaker),
                GameScreen::Settings(s) => s.update(gallery, &self.settings, self.time),
                GameScreen::Intro(i) => i.update(gallery, dt, &mut self.speaker, audio)?,
                GameScreen::Day(d) => d.update(dt, self.time, &mut self.speaker, audio),
            }
        }
        self.music.update(&mut self.speaker, audio);
        if !self.frozen {
            let clicked = match &mut self.screen {
                GameScreen::Empty => None,
                GameScreen::Title(t) => t.react(&mut self.input, &mut self.speaker, audio).map(|id| ("title", id)),
                GameScreen::Settings(s) => s
                    .react(&mut self.input, &mut self.speaker, audio, &mut self.settings, self.time)
                    .map(|id| ("settings", id)),
                GameScreen::Intro(i) => {
                    i.react(gallery, &mut self.input, dt, &mut self.speaker, audio)?.then(|| ("intro", "done".to_string()))
                }
                // Nothing on the day screen takes input yet (4b).
                GameScreen::Day(_) => None,
            };
            match clicked {
                Some(("title", id)) if id == "settings" => self.queue_screen_change("settings", gallery, audio)?,
                Some(("settings", id)) if id == "back" => self.queue_screen_change("title", gallery, audio)?,
                // `IntroScreen.intro_onDone` fades to the day-1 newspaper,
                // which comes in milestone 6; for now, to the title.
                Some(("intro", _)) => {
                    self.log.push("intro: done (the newspaper comes in milestone 6; to the title for now)".into());
                    self.queue_screen_change("title", gallery, audio)?;
                }
                Some((screen, id)) => self.log.push(format!("{screen}: {id} clicked")),
                None => {}
            }
        }
        self.speaker.update(dt, audio);
        if self.settings_generation != self.settings.generation() {
            self.apply_settings(audio, platform);
        } else {
            let fullscreen = platform.fullscreen();
            if fullscreen != self.settings.fullscreen() {
                self.settings.set_fullscreen(fullscreen);
            }
        }
        Ok(())
    }

    /// `Game.queueScreenChange` with a fade (`GameTransition.fadeToScreen`).
    fn queue_screen_change(&mut self, name: &'static str, gallery: &mut Gallery, audio: &mut dyn AudioHost) -> Result<(), String> {
        let events = self.fader.go(State::Off, false);
        self.pending = Some(name);
        for event in events {
            self.handle(event, gallery, audio)?;
        }
        Ok(())
    }

    fn handle(&mut self, event: Event, gallery: &mut Gallery, audio: &mut dyn AudioHost) -> Result<(), String> {
        match event {
            Event::FreezeScreen => self.frozen = true,
            Event::ApplyScreenChange => self.apply_screen_change(gallery, audio)?,
        }
        Ok(())
    }

    /// `Game.applyScreenChange`: every effect fades out (songs are left to
    /// the new screen's song), the old screen goes, one-shot effects are
    /// ignored for the rest of the frame, the new screen is built and its
    /// song asked for.
    fn apply_screen_change(&mut self, gallery: &mut Gallery, audio: &mut dyn AudioHost) -> Result<(), String> {
        let Some(name) = self.pending.take() else { return Ok(()) };
        self.speaker.stop_all(true, true, audio);
        self.speaker.ignore_non_looping_plays_this_frame();
        let (screen, song) = match name {
            "title" => (GameScreen::Title(TitleScreen::new(gallery, false)?), Some(title::SONG)),
            "settings" => (GameScreen::Settings(SettingsScreen::new(gallery, &self.settings)?), Some(settings_screen::SONG)),
            "intro" => (GameScreen::Intro(Box::new(IntroScreen::new(gallery, self.dt, &mut self.speaker, audio)?)), Some(intro::SONG)),
            "day" => (GameScreen::Day(Box::new(DayScreen::new(gallery, self.dt, &mut self.speaker, audio)?)), day::SONG),
            other => return Err(format!("Screen not found: {other}")),
        };
        self.screen = screen;
        self.frozen = false;
        self.music.play(song, &mut self.speaker, audio);
        Ok(())
    }

    /// `Game.applySettings` (the language part left out): each volume
    /// category gets its setting squared, the window's full screen follows
    /// the setting, and the settings are saved.
    fn apply_settings(&mut self, audio: &mut dyn AudioHost, platform: &mut dyn Platform) {
        audio.set_category_volume(Category::Music, category_volume(self.settings.music_volume()) as f32);
        audio.set_category_volume(Category::Effect, category_volume(self.settings.sound_volume()) as f32);
        platform.set_fullscreen(self.settings.fullscreen());
        if let Some(saved) = self.settings.save() {
            platform.save_settings(&saved);
        }
        self.settings_generation = self.settings.generation();
    }

    /// Draws the frame: the screen, the fade cover over it, the game's
    /// cursor over everything (layers 0, 10 and 100). `arrow` and `hand` are
    /// the cursor pictures (index, width, height).
    pub fn draw(&self, gallery: &Gallery, out: &mut Screen, arrow: (usize, u32, u32), hand: (usize, u32, u32)) {
        let quads = match &self.screen {
            GameScreen::Empty => Vec::new(),
            GameScreen::Title(t) => t.quads(gallery),
            GameScreen::Settings(s) => s.quads(gallery),
            GameScreen::Intro(i) => i.quads(gallery),
            GameScreen::Day(d) => d.quads(gallery),
        };
        out.clear();
        for q in &quads {
            out.draw(q, &gallery.pictures);
        }
        if self.fader.fade() != 0.0 {
            out.cover(self.fader.fade(), &gallery.pictures);
        }
        if let Some(q) = input::cursor_quad(&self.input, arrow, hand) {
            out.draw(&q, &gallery.pictures);
        }
    }
}
