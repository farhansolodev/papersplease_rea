//! The host: one Bevy window (in a browser, a canvas) showing the core's
//! 570 x 320 picture at the largest whole-number zoom, on black (or
//! stretched to the window, an option of the start screen).
//!
//! What it shows depends on the address (docs/milestone-1.md,
//! docs/milestone-2.md): `?page=title` (default) is the title screen as a
//! still, with `Theme` playing (milestone 1b, 2); `?page=fonts` is the font
//! test pages (arrow keys change the page, `&p=N` starts on page N, counting
//! from 0); `?page=sounds` is the sound test page (milestone 2);
//! `?page=testcard` is milestone 0's test card.

mod sound;

use bevy::asset::RenderAssetUsages;
use bevy::image::ImageSampler;
use bevy::input::keyboard::KeyCode;
use bevy::input::ButtonInput;
use bevy::prelude::*;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::window::PrimaryWindow;
use pp_core::adpcm;
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::screen::{self, HEIGHT, WIDTH};
use pp_core::sound::{category_volume, setting, Category};
use pp_core::soundtest::{self, Entry};
use pp_core::stepper::Stepper;
use pp_core::testcard;
use pp_core::title;
use sound::Player;

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
    Config {
        page: get(&cfg, "page").as_string().unwrap_or_else(|| "title".into()),
        index: get(&cfg, "p").as_f64().map_or(0, |n| n.max(0.0) as usize),
        pack,
        songs,
        music_volume: setting(get(&cfg, "musicVolume").as_f64().unwrap_or(1.0)),
        sound_volume: setting(get(&cfg, "soundVolume").as_f64().unwrap_or(1.0)),
        stretch: get(&cfg, "stretch").as_bool().unwrap_or(false),
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
    /// The title screen, drawn once.
    Title { gallery: Gallery, screen: Screen, dirty: bool },
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

fn start_mode(config: &mut Config) -> Mode {
    if config.page == "testcard" {
        return Mode::TestCard;
    }
    let Some(bytes) = config.pack.take() else {
        error!("the start pack was not handed over");
        return Mode::Failed;
    };
    let gallery = match Pack::parse(bytes).and_then(|pack| Gallery::from_pack(&pack)) {
        Ok(gallery) => gallery,
        Err(e) => {
            error!("start pack: {e}");
            return Mode::Failed;
        }
    };
    info!("start pack loaded: {} fonts, {} pictures", gallery.fonts.len(), gallery.pictures.len());
    match config.page.as_str() {
        "title" => Mode::Title { gallery, screen: Screen::new(), dirty: true },
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

fn setup(mut commands: Commands, mut images: ResMut<Assets<Image>>) {
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
    let mode = start_mode(&mut config);
    let mut player = Player::new();
    // As `Game.applySettings`: each category gets its setting squared.
    player.set_category_volume(Category::Music, category_volume(config.music_volume));
    player.set_category_volume(Category::Effect, category_volume(config.sound_volume));
    // The title screen's song. For now the host starts it as
    // `Speaker.music` would (loop, volume 1); the game's own music player
    // (`app.aud.Music`, fades and song changes) comes with milestone 3.
    if matches!(mode, Mode::Title { .. }) && config.songs.iter().any(|s| s == "Theme.ogg") {
        let id = player.new_id();
        if !player.start(id, Category::Music, "Theme.ogg", true, 1.0) {
            warn!("Theme.ogg did not start");
        }
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
    });
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
    mut host: ResMut<Host>,
    mut images: ResMut<Assets<Image>>,
) {
    let nanos = time.delta().as_nanos().min(u64::MAX as u128) as u64;
    host.stepper.advance(nanos);
    host.frames += 1;
    let (steps, frames) = (host.stepper.steps(), host.frames);
    let host = &mut *host;
    load_effects(host);
    host.player.update();
    let Some(mut image) = images.get_mut(&host.picture) else { return };
    let Some(data) = image.data.as_mut() else { return };
    match &mut host.mode {
        Mode::TestCard => testcard::render(steps, frames, data),
        Mode::Title { gallery, screen, dirty } => {
            if *dirty {
                *dirty = false;
                match title::draw(gallery, screen) {
                    Ok(()) => data.copy_from_slice(&screen.pixels),
                    Err(e) => error!("title screen: {e}"),
                }
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
    let (x, y, width, height) = if host.stretch {
        screen::stretch(w, h)
    } else {
        let fit = screen::fit(w, h);
        (fit.x, fit.y, fit.width, fit.height)
    };
    // The camera's world unit is one logical pixel (`scale` physical
    // ones). Work in physical pixels and divide once at the end.
    let centre_x = x as f32 + width as f32 / 2.0 - w as f32 / 2.0;
    let centre_y = y as f32 + height as f32 / 2.0 - h as f32 / 2.0;
    sprite.0.custom_size = Some(Vec2::new(width as f32, height as f32) / scale);
    sprite.1.translation = Vec3::new(centre_x / scale, -centre_y / scale, 0.0);
}
