# Dougelk Engine Wiki

## Overview

Dougelk Engine is a 2D Python game engine built around Pygame, grid-based positioning, sprite classes, and a stage loader. The current codebase is organized around a small boot layer, a central client runtime, reusable sprite/rendering utilities, an input abstraction layer, stage loading, audio playback, and a text/UI renderer. It is intended for retro-style projects and flexes `py_app.py`, `py_client.py`, `py_sprites.py`, and `assets/stages/spritemaker.py` as the main extension points. 

## Project layout

### Core Python modules

- `py_app.py` — application bootstrap, window behavior, build/version handling, and executable detection. 
- `py_client.py` — main runtime loop, entity management, input dispatch, stage loading, UI caching, and settings persistence. 
- `py_sprites.py` — base sprite class and built-in entity classes, including position, scaling, drawing, and lifecycle logic. 
- `py_ui_sprites.py` — text rendering system and dynamically generated glyph sprites for UI output. 
- `py_input.py` — keyboard, mouse, and controller input manager, including controller family detection and action maps. 
- `py_render.py` — sprite loading, recolouring, scaling, and grid/pixel conversion helpers. 
- `py_resource.py` — resource path resolver that switches between development paths and packaged executable paths. 
- `py_soundmixer.py` — audio loader and mixer wrapper for sound effects and music. 
- `py_stager.py` — stage file parser and entity spawner. 
- `py_prompt.py` — loading dialog shown before the game window starts. 
- `py_config.py` — global configuration singleton for resolution, scale, frame rate, and volume. 
- `py_numpy_slim.py` — lightweight NumPy replacement used by the UI renderer. 

### Build and project files

- `build_windows_nuitka_lto.bat` — Windows one-file build script using Nuitka. It sets metadata, locates Visual Studio tooling, checks dependencies, reads `GameBuild.version`, and produces `builds/Game.exe`. 
- `Game.ini` — persisted user settings (`window_scale`, `volume`). 
- `GameBuild.version` — build counter used for version metadata. The current value updates autonomously in the IDE but can be paused with `self.__exe_spoof = resource._set_exe_spoof(enabled=True)`. 
- `requirements.txt` — currently lists `pygame`. 
- `LICENSE` — Dougelk Engine Noncommercial License 1.1 (DENL-1.1). 

## Runtime architecture

### Startup sequence

The current launch path is:

1. `py_app.py` creates the `App` singleton and configures application metadata. It also centers the window, enables topmost behavior, and detects whether the app is running as a packaged executable. 
2. `py_client.py` shows the loading dialog from `py_prompt.py`, imports `app`, and initializes the `ClientGame` runtime. 
3. `ClientGame.__init__()` creates the entity buckets, initializes Pygame, sets the window, loads the stage manager, computes the current build version, and loads saved settings. 
4. `ClientGame.mainloop()` creates the main loop, handles input, updates entities, renders the scene, and processes events. 

### Main game loop

The loop is frame-driven and uses `pygame.time.Clock()` to cap the frame rate at `config.frame_rate`. The current config defaults are `264x264` base resolution, cell size `8`, scale `2`, and frame rate `60`, producing a `528x528` initial window. 

The loop does the following each frame:

- tracks debug FPS counters and optional overlays,
- detects resolution changes and forces a window rebuild,
- syncs `inputManager.mode` with the current game mode,
- dispatches the active mode handler from `update_methods`,
- clears and redraws all entities,
- processes quit, mouse, keyboard, and controller events. 

## Core concepts

### Entity teams

Entities are grouped into named teams inside `ClientGame.entities`:

- `actors`
- `ui`
- `decor`
- `particles`
- `__internal_mouse__`
- `__debug__` 

The engine flattens all teams except blacklisted ones when drawing. `__internal_mouse__` is excluded from most bulk entity operations so the cursor can be managed separately. 

### Sprite lifecycle

All in-world objects inherit from `py_sprites.Sprite`. The sprite system stores both grid and pixel coordinates, remembers the spawned position for respawn behavior, supports tinting, scaling, and sprite-sheet selection, and exposes `summon()`, `rescale()`, `draw()`, `set_sprite()`, and `replace_spritesheet()`. 

A sprite typically moves through this lifecycle:

1. instantiate class,
2. call `summon(...)`,
3. run `ticker()` and `task()` each frame,
4. optionally handle click actions,
5. draw on the screen,
6. mark for deletion when finished. 

### Grid / pixel system

The engine is grid-first. `py_render.grid_to_pixel()` and `py_render.pixel_to_grid()` translate between logical grid coordinates and actual screen coordinates using `config.CELL_SIZE` and `config.resolution_scale`. The standard cell size is `8`, and the base display uses a 264x264 logical grid. 

This design is used by:

- sprite placement,
- stage spawning,
- mouse-to-grid selection,
- UI text layout. 

## File-by-file documentation

### `py_app.py`

`App` stores the game identity and boot settings:

- `app_name = "Game"`
- `app_authors = ["You!"]`
- `app_description = "A framework build for LukieD4's Space Invaders university project."` 

It also defines:

- `DISP_RES_X_INIT = 264`
- `DISP_RES_Y_INIT = 264`
- `DISP_CELL_SIZE = 8`
- `DISP_FRAME_RATE = 60`
- `DISP_SCALE = 2` 

Important behavior:

- centers the window using `SDL_VIDEO_CENTERED`,
- attempts Windows topmost behavior through WinAPI,
- determines whether the app is frozen/compiled,
- reads and increments the build version file,
- falls back cleanly when the build version file is missing. 

### `py_client.py`

This is the runtime controller for the game. It:

- creates the entity dictionary,
- initializes the screen,
- loads the first stage,
- manages menu mode transitions,
- tracks input cooldowns and debug toggles,
- caches UI and entity lookups for performance,
- saves and loads `Game.ini`. 

Current mode dispatch includes:

- `menu-init`
- `menu` 

The main menu flow currently loads `assets/stages/example.stage`, iterates actors, responds to clicks, spawns a sprite and `Dog` entities, and plays sounds for interaction feedback. 

The user settings file stores:

- `window_scale`
- `volume` 

### `py_input.py`

`InputManager` uses pygame.joystick and normalizes three input families:

- keyboard,
- mouse,
- controller. 

It includes:

- controller polling on a background thread,
- Xbox-style default button mappings,
- support for DualShock-style sprite mapping,
- thumbstick direction handling,
- universal select/back helpers,
- per-mode action maps and debug action maps. 

Current action mappings include menu navigation, scaling controls, and debug hotkeys. For example, `F1` toggles the full debug UI, `F2` toggles the overlay, `F3` unlocks or relocks FPS, `F4` sets custom FPS, and `F5` sets custom FPS impact delay. 

### `py_render.py`

This module provides:

- `recolourSprite(surface, new_colour)`,
- `loadSprite(spritesheet)`,
- `scaleSprite(entity, surface, factor)`,
- `grid_to_pixel(row, col)`,
- `pixel_to_grid(x, y)`. 

The sprite loading logic falls back to `assets/sprites/missing.png` if a requested asset fails to load. The recolour path uses `BLEND_RGBA_MULT`, which preserves brightness relationships while tinting. 

### `py_resource.py`

`resource_path(relative)` is the repo’s path abstraction. It chooses between:

- development mode: paths relative to the source tree,
- executable mode: paths inside `%TEMP%/<app_name>`. 

This is why the README tells you to reference assets with `assets/...` paths: once packaged, resources are extracted and resolved from the temporary app directory.   
The sharable exe (from `builds/`) upon execution will unpack data into `%TEMP%/<app_name>` and will re-run the app with the unpacked version that's in temp.  

### `py_soundmixer.py`

`SoundMixer` wraps `pygame.mixer` and caches loaded audio. It supports:

- sound playback,
- infinite music playback with `pygame.mixer.music`,
- pause and unpause,
- stop by name,
- stop-all,
- mixer shutdown. 

Audio files are always resolved through `resource.resource_path()`, so the same path rules apply in both development and packaged builds. 

### `py_stager.py`

`Stager` loads a stage file format with two sections:

- `entity_map`
- `grid` 

Entity map entries resolve integer tile IDs to `py_sprites` classes. Grid rows define the layout, and `_spawn()` converts each tile into an instance placed on the screen. Entities without a team default to `decor`. 

### `py_ui_sprites.py`

This module builds the text/UI layer.

It defines:

- a `UI` base class,
- dynamic glyph classes generated from PNG files in `assets/sprites/font`,
- text rendering helpers,
- a background rendering path that returns a future-like object. 

The text syntax supports:

- inline colour markers,
- backtick line breaks,
- `~(literal_key)` for dynamic input labels,
- `~#` for colour reset  
- `~CYAN` an example colour setter 
- controller glyph substitution,
- a `REAL_SPACE` sentinel for genuine blank cells. 

### `py_sprites.py`

This is the main entity library. The base `Sprite` class stores:

- pixel position,
- grid position,
- spawn origin,
- scale,
- sprite sheets,
- current render surface,
- deletion state,
- click/drop flags. 

Notable built-in entities include:

- `Cursor`
- `Dog`
- `Particle`
- `Confetti` 

`set_window_icon()` loads `assets/sprites/cell.png` as the window icon. The engine keeps the icon logic in `py_sprites.py` to reduce bootstrap circular imports. 

### `py_prompt.py`

This module shows a Windows loading dialog while the game boots. It uses `MessageBoxW` and closes the dialog by posting `WM_CLOSE`. 

### `py_numpy_slim.py`

A minimal array helper used by the UI system. It provides:

- `full()`
- `array()`
- `copy()`
- `asarray()`
- `NDArray`
- `NDArrayRow` with `.fill()` and `.copy()`. 

## Settings and persistent state

### `Game.ini`

Current tracked settings:

- `window_scale=3`
- `volume=1.0` 

These values are loaded at startup and written back when the user rescales the window or changes volume. 

### `GameBuild.version`

The build counter is read at launch and embedded into build metadata. The build script also injects this value into Windows file/product version metadata. 

## Build and packaging

### Windows build script

`build_windows_nuitka_lto.bat` automates packaging with Nuitka and one-file output. It currently:

- sets `PROJECT_NAME=Game`,
- uses `py_client.py` as the entry point,
- embeds `assets/`,
- includes `GameBuild.version`,
- sets Windows icon/version/product metadata,
- excludes several large optional imports,
- enables LTO and parallel jobs,
- writes the final executable to `builds/Game.exe`. 

It also looks for `vsdevcmd.bat` automatically and installs missing dependencies if needed.

## Asset conventions

The current codebase expects assets to be addressed with repo-relative paths such as:

- `assets/sprites/...`
- `assets/audio/...`
- `assets/stages/...` 

When packaged, the resource system redirects these paths into `%TEMP%/<app_name>/assets/...`. 

## Stage authoring

The README points to `assets/stages/spritemaker.py` as the level-making tool. Stage files consumed by `Stager` use an `entity_map` plus `grid` layout, so any stage editor should emit that structure. 

## Extending the engine

### Add a new entity

1. Create a class in `py_sprites.py` that inherits `Sprite`.
2. Set its `team` property.
3. Define its `spritesheet`.
4. Override `task()` for per-frame behavior.
5. Optionally use `task_upon_click()` and custom flags such as `mark_mouse_clicked`. 

### Add a new input detection

1. Add a mode entry to `INPUT_MODES` and `DEBUG_INPUT_MODES` in `py_input.py`. Mode is derived from `py_client.ClientGame.mode` and is synchronised across.
2. Add a handler to `ClientGame.update_methods`.
3. Call `newMode()` to switch into it. 

### Add a new stage tile

1. Add the sprite/entity class in `py_sprites.py`.
2. Register the class name in the stage file’s `entity_map`.
3. Use the numeric ID in the `grid` section. 

## Operational notes

- The engine currently defaults to debug mode enabled. 
- Mouse and controller input are both supported, and the active input method affects which UI glyphs are shown. 
- Topmost window behavior is Windows-only. 
- The project is explicitly licensed as noncommercial under DENL-1.1.

## Attribution

This project uses the Dougelk Engine.
Copyright 2026 LukieD4.
Licensed under the Dougelk Engine Noncommercial License 1.1 (DENL-1.1).
Original repository: https://github.com/LukieD4/Dougelk-Engine