//! The host: one Bevy window (in a browser, a canvas) showing the core's
//! 570 x 320 picture at the largest whole-number zoom, on black (or
//! stretched to the window, an option of the start screen).
//!
//! What it shows depends on the address (docs/milestone-1.md,
//! docs/milestone-2.md, docs/milestone-3.md): `?page=title` (default) is the
//! game from its title screen, alive since milestone 3a (it rises with
//! `Theme`, its buttons press and click, the game draws its own cursor),
//! with the settings screen and the fades between screens since milestone
//! 3b; `?page=fonts` is the font test pages (arrow keys change the page,
//! `&p=N` starts on page N, counting from 0); `?page=sounds` is the sound
//! test page (milestone 2); `?page=testcard` is milestone 0's test card.

mod platform;
mod sound;

use bevy::asset::RenderAssetUsages;
use bevy::image::ImageSampler;
use bevy::input::keyboard::KeyCode;
use bevy::input::mouse::MouseButton;
use bevy::input::ButtonInput;
use bevy::prelude::*;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::window::{CursorOptions, PrimaryWindow};
use pp_core::adpcm;
use pp_core::aud::SoundDefs;
use pp_core::game::Game;
use pp_core::input::{HostInput, Key, KEY_COUNT};
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::screen::{self, HEIGHT, WIDTH};
use pp_core::settings::{Saved, Settings};
use pp_core::sound::{category_volume, setting, Category};
use pp_core::soundtest::{self, Entry};
use pp_core::stepper::Stepper;
use pp_core::testcard;
use platform::PagePlatform;
use sound::Player;

/// The core's fixed step, 1/60 s (docs/DESIGN.md, decision 1).
const STEP: f64 = 1.0 / 60.0;

/// The browser's keys for the game's 11 (docs/screens.md part 4, "Which key
/// pauses"). The developer key (Unity's `Tilde`, 126) has none: it is never
/// tested by the game.
const KEYS: [(Key, Option<KeyCode>); KEY_COUNT] = [
    (Key::Tab, Some(KeyCode::Tab)),
    (Key::Space, Some(KeyCode::Space)),
    (Key::Enter, Some(KeyCode::Enter)),
    (Key::Left, Some(KeyCode::ArrowLeft)),
    (Key::Right, Some(KeyCode::ArrowRight)),
    (Key::Escape, Some(KeyCode::Escape)),
    (Key::T, Some(KeyCode::KeyT)),
    (Key::DevMenu, None),
    (Key::AutoplayAbort, Some(KeyCode::KeyL)),
    (Key::AutoplayPause, Some(KeyCode::KeyP)),
    (Key::Screenshot, Some(KeyCode::KeyO)),
];

/// The game and what it draws with.
struct GameRun {
    gallery: Gallery,
    screen: Screen,
    game: Game,
    /// The arrow's and the hand's pictures (index, width, height).
    arrow: (usize, u32, u32),
    hand: (usize, u32, u32),
}

/// Settings the loader script passes in (`window.ppConfig`).
struct Config {
    page: String,
    index: usize,
    pack: Option<Vec<u8>>,
    /// The songs the page can play ("Theme.ogg", ...).
    songs: Vec<String>,
    /// The start screen's volume settings, tenths from 0 to 1.
    music_volume: f64,
    sound_volume: f64,
    stretch: bool,
    /// The game's settings as the page keeps them, if it has any.
    saved: Option<Saved>,
}

#[cfg(target_arch = "wasm32")]
fn read_config() -> Config {
    use js_sys::{Array, Reflect, Uint8Array};
    use wasm_bindgen::{JsCast, JsValue};
    let get = |obj: &JsValue, key: &str| Reflect::get(obj, &JsValue::from_str(key)).unwrap_or(JsValue::UNDEFINED);
    let cfg = get(&js_sys::global(), "ppConfig");
    let pack = get(&cfg, "pack")
        .dyn_into::<Uint8Array>()
        .ok()
        .map(|a| a.to_vec());
    let songs = get(&cfg, "songs")
        .dyn_into::<Array>()
        .map(|a| a.iter().filter_map(|s| s.as_string()).collect())
        .unwrap_or_default();
    let saved = get(&cfg, "settings");
    let saved = (saved.is_object()).then(|| Saved {
        fullscreen: get(&saved, "fullscreen").as_bool().unwrap_or(false),
        nudity: get(&saved, "nudity").as_bool().unwrap_or(true),
        easy_mode: get(&saved, "easyMode").as_bool().unwrap_or(false),
        date_format_index: get(&saved, "dateFormatIndex").as_f64().unwrap_or(0.0) as i32,
        music_volume: setting(get(&saved, "musicVolume").as_f64().unwrap_or(1.0)),
        sound_volume: setting(get(&saved, "soundVolume").as_f64().unwrap_or(1.0)),
    });
    Config {
        page: get(&cfg, "page").as_string().unwrap_or_else(|| "title".into()),
        index: get(&cfg, "p").as_f64().map_or(0, |n| n.max(0.0) as usize),
        pack,
        songs,
        music_volume: setting(get(&cfg, "musicVolume").as_f64().unwrap_or(1.0)),
        sound_volume: setting(get(&cfg, "soundVolume").as_f64().unwrap_or(1.0)),
        stretch: get(&cfg, "stretch").as_bool().unwrap_or(false),
        saved,
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn read_config() -> Config {
    Config {
        page: "testcard".into(),
        index: 0,
        pack: None,
        songs: Vec::new(),
        music_volume: 1.0,
        sound_volume: 1.0,
        stretch: false,
        saved: None,
    }
}

/// One sound started on the sound test page.
struct Play {
    id: u32,
    file: String,
    /// The frame it was started in: the player is asked about it only from
    /// the next frame on.
    frame: u64,
}

enum Mode {
    /// Milestone 0's test card.
    TestCard,
    /// The game, from its title screen.
    Title(Box<GameRun>),
    /// The font test pages.
    Pages { gallery: Gallery, count: usize, index: usize, screen: Screen, dirty: bool },
    /// The sound test page.
    Sounds { gallery: Gallery, screen: Screen, selected: usize, plays: Vec<Play>, effects_paused: bool, dirty: bool },
    /// Something could not be loaded; the screen stays black.
    Failed,
}

/// The time step, the picture, the sound player and what is drawn.
#[derive(Resource)]
struct Host {
    stepper: Stepper,
    /// Pictures drawn so far (the yellow number on the test card).
    frames: u64,
    picture: Handle<Image>,
    mode: Mode,
    player: Player,
    /// The effects' names once the effects pack has arrived and is decoded.
    effects: Option<Vec<String>>,
    songs: Vec<String>,
    music_volume: f64,
    sound_volume: f64,
    stretch: bool,
    /// The mouse has been over the game since the start (the original's
    /// input mode 1), and where it was last, in game pixels.
    mouse_seen: bool,
    mouse: (f64, f64),
    /// Presses not yet seen by a step: a key or button pressed and let go
    /// within one browser frame, or during a frame that runs no step, still
    /// counts as held for the next step.
    pending_keys: [bool; KEY_COUNT],
    pending_left: bool,
}

/// The sprite that shows the screen picture.
#[derive(Component)]
struct ScreenSprite;

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                title: "Papers, Please (browser port)".into(),
                canvas: Some("#game".into()),
                fit_canvas_to_parent: true,
                // false: true makes the page swallow F5, F12, Ctrl+R and the
                // right-click menu while the game has focus.
                prevent_default_event_handling: false,
                ..default()
            }),
            ..default()
        }))
        .insert_resource(ClearColor(Color::BLACK))
        .add_systems(Startup, setup)
        .add_systems(Update, (step_and_draw, place_picture).chain())
        .run();
}

fn start_mode(config: &mut Config, player: &mut Player) -> Mode {
    if config.page == "testcard" {
        return Mode::TestCard;
    }
    let Some(bytes) = config.pack.take() else {
        error!("the start pack was not handed over");
        return Mode::Failed;
    };
    let loaded = Pack::parse(bytes).and_then(|pack| Ok((Gallery::from_pack(&pack)?, pack)));
    let (gallery, pack) = match loaded {
        Ok(loaded) => loaded,
        Err(e) => {
            error!("start pack: {e}");
            return Mode::Failed;
        }
    };
    info!("start pack loaded: {} fonts, {} pictures", gallery.fonts.len(), gallery.pictures.len());
    match config.page.as_str() {
        "title" => match game_run(gallery, &pack, config.saved.as_ref(), player) {
            Ok(run) => Mode::Title(Box::new(run)),
            Err(e) => {
                error!("title screen: {e}");
                Mode::Failed
            }
        },
        "sounds" => Mode::Sounds {
            gallery,
            screen: Screen::new(),
            selected: 0,
            plays: Vec::new(),
            effects_paused: false,
            dirty: true,
        },
        _ => {
            let count = gallery.pages().len();
            Mode::Pages { index: config.index.min(count - 1), gallery, count, screen: Screen::new(), dirty: true }
        }
    }
}

/// The game from its first title screen, with the speaker reading
/// `Sounds.xml` and the settings the page kept (a desktop game starts with
/// nudity on).
fn game_run(gallery: Gallery, pack: &Pack, saved: Option<&Saved>, player: &mut Player) -> Result<GameRun, String> {
    let xml = pack.get("data/Sounds.xml").ok_or("data/Sounds.xml is missing from the pack")?;
    let defs = SoundDefs::parse(std::str::from_utf8(xml).map_err(|_| "Sounds.xml is not UTF-8")?)?;
    let cursor = |file: &str| -> Result<(usize, u32, u32), String> {
        let i = gallery.picture(file).ok_or_else(|| format!("{file} is missing from the pack"))?;
        Ok((i, gallery.pictures[i].width, gallery.pictures[i].height))
    };
    let (arrow, hand) = (cursor("CursorArrow.png")?, cursor("CursorHand.png")?);
    Ok(GameRun {
        game: Game::new(&gallery, defs, Settings::new(true, saved), player)?,
        gallery,
        screen: Screen::new(),
        arrow,
        hand,
    })
}

/// Where the picture sits in the window (x, y, width, height), in physical
/// pixels.
fn picture_rect(stretch: bool, w: u32, h: u32) -> (i32, i32, u32, u32) {
    if stretch {
        screen::stretch(w, h)
    } else {
        let fit = screen::fit(w, h);
        (fit.x, fit.y, fit.width, fit.height)
    }
}

fn setup(
    mut commands: Commands,
    mut images: ResMut<Assets<Image>>,
    mut cursor: Single<&mut CursorOptions, With<PrimaryWindow>>,
) {
    // An sRGB texture: the picture's byte values are what the game would
    // store, and the graphics card turns them to light and back on the way
    // to the (sRGB) window, which returns the same bytes.
    let mut image = Image::new_fill(
        Extent3d {
            width: WIDTH,
            height: HEIGHT,
            depth_or_array_layers: 1,
        },
        TextureDimension::D2,
        &[0, 0, 0, 255],
        TextureFormat::Rgba8UnormSrgb,
        RenderAssetUsages::default(),
    );
    // Nearest-pixel reads: the zoom shows blocks, never a blur.
    image.sampler = ImageSampler::nearest();
    let picture = images.add(image);

    let mut config = read_config();
    let mut player = Player::new();
    // As `Game.applySettings`: each category gets its setting squared (the
    // game applies its settings again on its first frame).
    player.set_category_volume(Category::Music, category_volume(config.music_volume));
    player.set_category_volume(Category::Effect, category_volume(config.sound_volume));
    let mode = start_mode(&mut config, &mut player);
    if let Mode::Title(_) = &mode {
        // The game draws its own cursor; the system's is hidden over it.
        cursor.visible = false;
    }

    commands.spawn(Camera2d);
    commands.spawn((ScreenSprite, Sprite::from_image(picture.clone())));
    commands.insert_resource(Host {
        stepper: Stepper::new(),
        frames: 0,
        picture,
        mode,
        player,
        effects: None,
        songs: config.songs,
        music_volume: config.music_volume,
        sound_volume: config.sound_volume,
        stretch: config.stretch,
        mouse_seen: false,
        mouse: (0.0, 0.0),
        pending_keys: [false; KEY_COUNT],
        pending_left: false,
    });
}

/// What the host read this frame, for the core (`HostUnity.Update`): the
/// game keys held, and the mouse in game pixels once it has been over the
/// game (its last place when it is outside the window). A press this frame
/// is remembered until a step has seen it ([`Host::pending_keys`]).
fn read_input(host: &mut Host, window: &Window, keys: &ButtonInput<KeyCode>, buttons: &ButtonInput<MouseButton>) -> HostInput {
    let mut out = HostInput::default();
    for (key, code) in KEYS {
        let Some(c) = code else { continue };
        host.pending_keys[key as usize] |= keys.just_pressed(c);
        out.keys[key as usize] = keys.pressed(c) || host.pending_keys[key as usize];
    }
    if let Some(at) = window.physical_cursor_position() {
        let rect = picture_rect(host.stretch, window.physical_width(), window.physical_height());
        host.mouse = screen::game_pixel(at.x as f64, at.y as f64, rect);
        host.mouse_seen = true;
    }
    host.pending_left |= buttons.just_pressed(MouseButton::Left);
    let left = buttons.pressed(MouseButton::Left) || host.pending_left;
    // A press counts as the mouse being over the game, as in the original.
    host.mouse_seen |= left;
    out.mouse_valid = host.mouse_seen;
    out.mouse = host.mouse;
    out.left_down = left;
    out
}

/// The game keys held now.
fn held_keys(keys: &ButtonInput<KeyCode>) -> [bool; KEY_COUNT] {
    let mut out = [false; KEY_COUNT];
    for (key, code) in KEYS {
        out[key as usize] = code.is_some_and(|c| keys.pressed(c));
    }
    out
}

/// One 1/60 s step of the game (`Game.update`'s frame order, pp_core's
/// `game.rs`).
fn step_game(run: &mut GameRun, input: &HostInput, player: &mut Player) {
    if let Err(e) = run.game.step(input, STEP, &mut run.gallery, player, &mut PagePlatform) {
        error!("game: {e}");
    }
    for line in run.game.log.drain(..) {
        // Where these buttons lead comes with later milestones.
        info!("{line}");
    }
}

/// Decodes the effects pack once the page has it, and hands every effect to
/// the sound player.
fn load_effects(host: &mut Host) {
    if host.effects.is_some() {
        return;
    }
    let Some(bytes) = sound::take_effects_pack() else { return };
    let clips = match Pack::parse(bytes).and_then(|pack| adpcm::read_effects(&pack)) {
        Ok(clips) => clips,
        Err(e) => {
            error!("effects pack: {e}");
            host.effects = Some(Vec::new());
            return;
        }
    };
    for clip in &clips {
        host.player.add_clip(clip);
    }
    info!("effects loaded: {}", clips.len());
    host.effects = Some(clips.into_iter().map(|c| c.name).collect());
    if let Mode::Sounds { dirty, .. } = &mut host.mode {
        *dirty = true;
    }
}

/// Runs the core's 1/60 s steps that real time asks for, then draws.
fn step_and_draw(
    time: Res<Time<Real>>,
    keys: Res<ButtonInput<KeyCode>>,
    buttons: Res<ButtonInput<MouseButton>>,
    window: Single<&Window, With<PrimaryWindow>>,
    mut host: ResMut<Host>,
    mut images: ResMut<Assets<Image>>,
) {
    let nanos = time.delta().as_nanos().min(u64::MAX as u128) as u64;
    let due = host.stepper.advance(nanos);
    host.frames += 1;
    let (steps, frames) = (host.stepper.steps(), host.frames);
    let host = &mut *host;
    load_effects(host);
    host.player.update();
    let host_input = read_input(host, &window, &keys, &buttons);
    let Some(mut image) = images.get_mut(&host.picture) else { return };
    let Some(data) = image.data.as_mut() else { return };
    match &mut host.mode {
        Mode::TestCard => testcard::render(steps, frames, data),
        Mode::Title(run) => {
            let mut input = host_input;
            for _ in 0..due {
                step_game(run, &input, &mut host.player);
                // Seen once: from the next step on, only what is held.
                (input.keys, input.left_down) = (held_keys(&keys), buttons.pressed(MouseButton::Left));
            }
            if due > 0 {
                host.pending_keys = [false; KEY_COUNT];
                host.pending_left = false;
            }
            if due > 0 {
                run.game.draw(&run.gallery, &mut run.screen, run.arrow, run.hand);
                data.copy_from_slice(&run.screen.pixels);
            }
        }
        Mode::Pages { gallery, count, index, screen, dirty } => {
            let count = *count;
            if keys.just_pressed(KeyCode::ArrowRight) {
                *index = (*index + 1) % count;
                *dirty = true;
            }
            if keys.just_pressed(KeyCode::ArrowLeft) {
                *index = (*index + count - 1) % count;
                *dirty = true;
            }
            if *dirty {
                gallery.draw_page(*index, screen);
                data.copy_from_slice(&screen.pixels);
                *dirty = false;
            }
        }
        Mode::Sounds { gallery, screen, selected, plays, effects_paused, dirty } => {
            let player = &mut host.player;
            let names: Vec<String> = host.effects.iter().flatten().chain(&host.songs).cloned().collect();
            let count = names.len();
            for (key, dx, dy) in [
                (KeyCode::ArrowUp, 0, -1),
                (KeyCode::ArrowDown, 0, 1),
                (KeyCode::ArrowLeft, -1, 0),
                (KeyCode::ArrowRight, 1, 0),
            ] {
                if keys.just_pressed(key) {
                    *selected = soundtest::moved(*selected, count, dx, dy);
                    *dirty = true;
                }
            }
            *selected = (*selected).min(count.saturating_sub(1));
            for (key, looping) in [(KeyCode::Enter, false), (KeyCode::KeyL, true)] {
                if keys.just_pressed(key) && count > 0 {
                    let file = &names[*selected];
                    let category = if file.ends_with(".ogg") { Category::Music } else { Category::Effect };
                    let id = player.new_id();
                    player.start(id, category, file, looping, 1.0);
                    plays.push(Play { id, file: file.clone(), frame: frames });
                    *dirty = true;
                }
            }
            if keys.just_pressed(KeyCode::KeyS) {
                for p in plays.drain(..) {
                    player.stop(p.id);
                }
                *dirty = true;
            }
            if keys.just_pressed(KeyCode::Space) {
                *effects_paused = !*effects_paused;
                player.set_category_pause(Category::Effect, *effects_paused);
                *dirty = true;
            }
            for (key, music, step) in [
                (KeyCode::Digit1, false, -0.1),
                (KeyCode::Digit2, false, 0.1),
                (KeyCode::Digit3, true, -0.1),
                (KeyCode::Digit4, true, 0.1),
            ] {
                if keys.just_pressed(key) {
                    let (value, category) = if music {
                        (&mut host.music_volume, Category::Music)
                    } else {
                        (&mut host.sound_volume, Category::Effect)
                    };
                    *value = setting(*value + step);
                    player.set_category_volume(category, category_volume(*value));
                    *dirty = true;
                }
            }
            // A sound the player no longer has is dropped, but not in the
            // frame it was started (as the original's speaker does).
            let before = plays.len();
            let mut positions = Vec::new();
            plays.retain(|p| {
                let at = player.position(p.id);
                if at >= 0.0 {
                    positions.push((p.file.clone(), at));
                }
                at >= 0.0 || p.frame == frames
            });
            if plays.len() != before {
                *dirty = true;
            }
            // Redrawn on a change and 10 times a second for the positions.
            if *dirty || (frames % 6 == 0 && !plays.is_empty()) {
                *dirty = false;
                let entries: Vec<Entry> = names
                    .iter()
                    .map(|n| Entry { name: n.clone(), playing: plays.iter().any(|p| &p.file == n) })
                    .collect();
                let db = |v: f64| 20.0 * category_volume(v).max(0.0001).log10();
                let mut lines = vec![
                    format!(
                        "Effects: {}.  Sound {:.1} = {:.1} dB, music {:.1} = {:.1} dB.  Effects {}.",
                        match &host.effects {
                            None => "loading".to_string(),
                            Some(e) => format!("{} loaded", e.len()),
                        },
                        host.sound_volume,
                        db(host.sound_volume),
                        host.music_volume,
                        db(host.music_volume),
                        if *effects_paused { "paused" } else { "playing" },
                    ),
                    format!("Playing {} of at most 32:", positions.len()),
                ];
                let mut line = String::new();
                for (file, at) in &positions {
                    let item = format!("{file} {at:.1} s   ");
                    if line.len() + item.len() > 105 {
                        lines.push(std::mem::take(&mut line));
                        if lines.len() == 4 {
                            break;
                        }
                    }
                    line.push_str(&item);
                }
                if !line.is_empty() && lines.len() < 4 {
                    lines.push(line);
                }
                soundtest::draw(gallery, &entries, *selected, &lines, screen);
                data.copy_from_slice(&screen.pixels);
            }
        }
        Mode::Failed => {}
    }
}

/// Sizes and places the sprite for the window's current physical size.
fn place_picture(
    host: Res<Host>,
    window: Single<&Window, With<PrimaryWindow>>,
    mut sprite: Single<(&mut Sprite, &mut Transform), With<ScreenSprite>>,
) {
    let (w, h) = (window.physical_width(), window.physical_height());
    let scale = window.scale_factor();
    let (x, y, width, height) = picture_rect(host.stretch, w, h);
    // The camera's world unit is one logical pixel (`scale` physical
    // ones). Work in physical pixels and divide once at the end.
    let centre_x = x as f32 + width as f32 / 2.0 - w as f32 / 2.0;
    let centre_y = y as f32 + height as f32 / 2.0 - h as f32 / 2.0;
    sprite.0.custom_size = Some(Vec2::new(width as f32, height as f32) / scale);
    sprite.1.translation = Vec3::new(centre_x / scale, -centre_y / scale, 0.0);
}
