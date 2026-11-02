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
//! The pause key is not looked at yet: none of the screens built so far can
//! be paused (only the day, night, news and intro screens can).

use crate::aud::{AudioHost, Music, SoundDefs, Speaker};
use crate::fade::{Event, Fader, State};
use crate::input::{self, HostInput, Input};
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
    Title(TitleScreen),
    Settings(SettingsScreen),
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
    /// The game's clock (`app.Clock.time`).
    time: f64,
    /// Lines for the host's log (clicks that lead nowhere yet).
    pub log: Vec<String>,
}

impl Game {
    /// The start: the first title screen of the run (the one that rises)
    /// and its song.
    pub fn new(gallery: &Gallery, defs: SoundDefs, settings: Settings, audio: &mut dyn AudioHost) -> Result<Game, String> {
        let mut game = Game {
            input: Input::new(),
            speaker: Speaker::new(defs),
            music: Music::new(),
            settings,
            settings_generation: 0,
            fader: Fader::new(),
            screen: GameScreen::Title(TitleScreen::new(gallery, true)?),
            frozen: false,
            pending: None,
            time: 0.0,
            log: Vec::new(),
        };
        game.music.play(Some(title::SONG), &mut game.speaker, audio);
        Ok(game)
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
        for event in self.fader.step(dt) {
            self.handle(event, gallery, audio)?;
        }
        if !self.frozen {
            match &mut self.screen {
                GameScreen::Title(t) => t.update(&self.music, &self.speaker),
                GameScreen::Settings(s) => s.update(gallery, &self.settings, self.time),
            }
        }
        self.music.update(&mut self.speaker, audio);
        if !self.frozen {
            let clicked = match &mut self.screen {
                GameScreen::Title(t) => t.react(&mut self.input, &mut self.speaker, audio).map(|id| ("title", id)),
                GameScreen::Settings(s) => s
                    .react(&mut self.input, &mut self.speaker, audio, &mut self.settings, self.time)
                    .map(|id| ("settings", id)),
            };
            match clicked {
                Some(("title", id)) if id == "settings" => self.queue_screen_change("settings", gallery, audio)?,
                Some(("settings", id)) if id == "back" => self.queue_screen_change("title", gallery, audio)?,
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
            "title" => (GameScreen::Title(TitleScreen::new(gallery, false)?), title::SONG),
            "settings" => (GameScreen::Settings(SettingsScreen::new(gallery, &self.settings)?), settings_screen::SONG),
            other => return Err(format!("Screen not found: {other}")),
        };
        self.screen = screen;
        self.frozen = false;
        self.music.play(Some(song), &mut self.speaker, audio);
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
            GameScreen::Title(t) => t.quads(gallery),
            GameScreen::Settings(s) => s.quads(gallery),
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
