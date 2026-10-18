//! The host: one Bevy window (in a browser, a canvas) showing the core's
//! 570 x 320 picture at the largest whole-number zoom, on black.
//!
//! What it shows depends on the address (docs/milestone-1.md):
//! `?page=fonts` (default; arrow keys change the page, `&p=N` starts on page
//! N, counting from 0) is the font test pages; `?page=testcard` is
//! milestone 0's test card.

use bevy::asset::RenderAssetUsages;
use bevy::image::ImageSampler;
use bevy::input::keyboard::KeyCode;
use bevy::input::ButtonInput;
use bevy::prelude::*;
use bevy::render::render_resource::{Extent3d, TextureDimension, TextureFormat};
use bevy::window::PrimaryWindow;
use pp_core::pack::Pack;
use pp_core::pages::Gallery;
use pp_core::raster::Screen;
use pp_core::screen::{self, HEIGHT, WIDTH};
use pp_core::stepper::Stepper;
use pp_core::testcard;

/// Settings the loader script passes in (`window.ppConfig`).
struct Config {
    page: String,
    index: usize,
    pack: Option<Vec<u8>>,
}

#[cfg(target_arch = "wasm32")]
fn read_config() -> Config {
    use js_sys::{Reflect, Uint8Array};
    use wasm_bindgen::{JsCast, JsValue};
    let get = |obj: &JsValue, key: &str| Reflect::get(obj, &JsValue::from_str(key)).unwrap_or(JsValue::UNDEFINED);
    let cfg = get(&js_sys::global(), "ppConfig");
    let pack = get(&cfg, "pack")
        .dyn_into::<Uint8Array>()
        .ok()
        .map(|a| a.to_vec());
    Config {
        page: get(&cfg, "page").as_string().unwrap_or_else(|| "fonts".into()),
        index: get(&cfg, "p").as_f64().map_or(0, |n| n.max(0.0) as usize),
        pack,
    }
}

#[cfg(not(target_arch = "wasm32"))]
fn read_config() -> Config {
    Config { page: "testcard".into(), index: 0, pack: None }
}

enum Mode {
    /// Milestone 0's test card.
    TestCard,
    /// The font test pages.
    Pages { gallery: Gallery, count: usize, index: usize, screen: Screen, dirty: bool },
    /// Something could not be loaded; the screen stays black.
    Failed,
}

/// The time step, the picture and what is drawn on it.
#[derive(Resource)]
struct Host {
    stepper: Stepper,
    /// Pictures drawn so far (the yellow number on the test card).
    frames: u64,
    picture: Handle<Image>,
    mode: Mode,
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

fn start_mode(config: Config) -> Mode {
    if config.page == "testcard" {
        return Mode::TestCard;
    }
    let Some(bytes) = config.pack else {
        error!("the start pack was not handed over");
        return Mode::Failed;
    };
    let gallery = Pack::parse(bytes).and_then(|pack| Gallery::from_pack(&pack));
    match gallery {
        Ok(gallery) => {
            let count = gallery.pages().len();
            info!("start pack loaded: {} fonts, {} pictures, {} pages", gallery.fonts.len(), gallery.pictures.len(), count);
            Mode::Pages { index: config.index.min(count - 1), gallery, count, screen: Screen::new(), dirty: true }
        }
        Err(e) => {
            error!("start pack: {e}");
            Mode::Failed
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

    commands.spawn(Camera2d);
    commands.spawn((ScreenSprite, Sprite::from_image(picture.clone())));
    commands.insert_resource(Host {
        stepper: Stepper::new(),
        frames: 0,
        picture,
        mode: start_mode(read_config()),
    });
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
    let Some(mut image) = images.get_mut(&host.picture) else { return };
    let Some(data) = image.data.as_mut() else { return };
    match &mut host.mode {
        Mode::TestCard => testcard::render(steps, frames, data),
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
        Mode::Failed => {}
    }
}

/// Sizes and places the sprite for the window's current physical size.
fn place_picture(
    window: Single<&Window, With<PrimaryWindow>>,
    mut sprite: Single<(&mut Sprite, &mut Transform), With<ScreenSprite>>,
) {
    let (w, h) = (window.physical_width(), window.physical_height());
    let scale = window.scale_factor();
    let fit = screen::fit(w, h);
    // The camera's world unit is one logical pixel (`scale` physical
    // ones). Work in physical pixels and divide once at the end.
    let centre_x = fit.x as f32 + fit.width as f32 / 2.0 - w as f32 / 2.0;
    let centre_y = fit.y as f32 + fit.height as f32 / 2.0 - h as f32 / 2.0;
    sprite.0.custom_size = Some(Vec2::new(fit.width as f32, fit.height as f32) / scale);
    sprite.1.translation = Vec3::new(centre_x / scale, -centre_y / scale, 0.0);
}
