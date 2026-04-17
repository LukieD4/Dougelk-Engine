from __future__ import annotations

import pygame, time, random

from random import randint

from py_resource import resource
from py_render import loadSprite, scaleSprite, grid_to_pixel, pixel_to_grid
from py_config import config

# Directories
assets_dir = resource.resource_path("assets")
sprites_dir = assets_dir / "sprites"
actor_dir = sprites_dir / "actor"
object_dir = sprites_dir / "object"


def set_window_icon():
    """
    Set the pygame window icon using a default sprite.

    This is intentionally defined here (instead of py_app) to:
    - Avoid circular imports
    - Reduce dependency surface of the app bootstrap

    Uses `sprites/cell.png` as the icon.
    """
    pygame.display.set_icon(loadSprite([sprites_dir / "cell.png"]))


class Sprite:
    """
    Base renderable object with position, sprite, and lifecycle management.

    Responsibilities:
    - Maintain pixel + grid coordinates
    - Handle sprite loading, tinting, and scaling
    - Provide movement, animation, and draw hooks
    - Track lifecycle flags (deletion, respawn)

    Surface lifecycle:
        surface_original         -> raw loaded image
        surface_tinted_original  -> tinted variant (optional)
        surface_render           -> final scaled surface (blitted)

    Notes:
    - Scaling is driven by `config.resolution_scale * self.__SCALE`
    - Grid ↔ pixel conversions use helper utilities
    - Subclasses are expected to override `task()`
    """
    #region __Init__
    def __init__(self):
        # (Float) Pixel coords
        self.pos_x, self.pos_y, self.pos_x_previous, self.pos_y_previous = 0, 0, 0, 0
        self.pos_row, self.pos_col = 0,0
        # (Float) (consts)
        self.POS_X_OFFSET, self.POS_Y_OFFSET = 0, 0
        
        # Spawned
        self.SUMMONED_POS_X, self.SUMMONED_POS_Y = 0, 0
        self.SUMMONED_POS_ROW, self.SUMMONED_POS_COL = 0,0
        
        # (Ideal: Integer) (const) 
        self.__SCALE = 1

        # (Integer) How many updates this sprite has recieved
        self.tick = 0

        # sprite resources
        self.spritesheet = [[sprites_dir / "missing.png"]]
        self.sprite_rect: pygame.Rect | None = None
        self.sprite_rect_previous: pygame.Rect | None = None
        self.sprite_index = 0
        # don't tamper
        self._sprite_oscillator = 0

        # team
        self.team = "decor" # (default: a vegatative state)

        # mark
        self.mark_for_deletion = False
        self.mark_for_respawn = False
        self.mark_mouse_clicked = False

        # SURFACE LIFECYCLE (single rendered surface):
        # - self.surface_original: the raw image loaded from disk (unscaled, unmodified)
        # - self.surface_tinted_original: the tinted version of the original (unscaled) if a tint is applied
        # - self.surface_render: the final scaled surface that is actually blitted to screen
        self.surface_original: pygame.Surface | None = None
        self.surface_tinted_original: pygame.Surface | None = None
        self.surface_render: pygame.Surface | None = None
        self.surface_tint_colour: tuple[int,int,int] | None = None

        assert self.__SCALE >= 0.25, "resolution_scale must be greater than 0.25"

    #region Surfacing
    def _tint_surface(self, surface: pygame.Surface, colour: tuple[int,int,int]) -> pygame.Surface:
        """
        Apply a multiplicative RGB tint to a surface.

        Args:
            surface: Source surface (must support alpha)
            colour: (R, G, B) multiplier values

        Returns:
            New tinted surface with original alpha preserved.

        Notes:
            Uses `BLEND_RGBA_MULT`, meaning:
            - White (255,255,255) = no change
            - Black (0,0,0) = fully dark
        """
        if surface is None:
            return None
        tinted = surface.copy().convert_alpha()
        tint_surf = pygame.Surface(tinted.get_size(), pygame.SRCALPHA)
        # ensure full-alpha overlay with the chosen colour
        tint_surf.fill((*colour, 255))
        tinted.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return tinted

    def _build_render_surface(self, source_surface: pygame.Surface) -> pygame.Surface:
        """
        Build the final render surface from a source image.

        Applies:
        - Global resolution scale (`config.resolution_scale`)
        - Per-sprite scale (`self.__SCALE`)

        Args:
            source_surface: Original or tinted surface

        Returns:
            Scaled surface ready for rendering.

        Important:
            Always scales from ORIGINAL data to avoid cumulative degradation.
        """
        if source_surface is None:
            return None
        final_factor = config.resolution_scale * self.__SCALE
        # print(final_factor, config.resolution_scale, self.__SCALE)
        if final_factor > 1024:
            pass
        return scaleSprite(self, source_surface, factor=final_factor, smooth=False)
    
    def rebuild_surfaces(self, tint: tuple[int, int, int] | None = None):
        """
        Recompute all surface variants (tint + scale).

        Args:
            tint: Optional new tint colour (overwrites existing)

        Process:
            1. Update tint state (if provided)
            2. Rebuild tinted original (if needed)
            3. Rebuild scaled render surface
            4. Sync sprite rect size

        Use this when:
            - Changing tint dynamically
            - After modifying base surface
            - For safe rescaling without artifacts
        """
        # Update tint if specified
        if tint is not None:
            self.surface_tint_colour = tint

        # Choose source: original or tint-original
        if self.surface_tint_colour is not None:
            # Build tinted original
            self.surface_tinted_original = self._tint_surface(
                self.surface_original,
                self.surface_tint_colour
            )
            source = self.surface_tinted_original
        else:
            self.surface_tinted_original = None
            source = self.surface_original

        # Now build the scaled render surface
        self.surface_render = self._build_render_surface(source)

        # Update rect
        if self.sprite_rect and self.surface_render:
            self.sprite_rect.size = self.surface_render.get_size()

    ####


    #region Summon
    def summon(
        self,
        target_row=None,
        target_col=None,
        target_pos_x=None,
        target_pos_y=None,
        screen=None,
        colour: tuple[int, int, int] = None,
        offset_x=None,
        offset_y=None,
        initial_sprite_index=None  # NEW PARAMETER
    ):
        """
        Spawn the sprite into the world with position, visual state, and surface setup.

        Positioning:
            - Accepts EITHER grid (row/col) OR pixel (pos_x/pos_y)
            - Applies optional pixel offsets (scaled by resolution)

        Args:
            target_row / target_col: Grid position
            target_pos_x / target_pos_y: Pixel position
            screen: Target render surface
            colour: Optional tint applied at spawn
            offset_x / offset_y: Pixel offsets (pre-scale)
            initial_sprite_index: Starting frame index

        Behavior:
            - Resolves position into both pixel + grid space
            - Stores "summoned" origin for respawn
            - Loads sprite via `set_sprite` for consistency
            - Applies tint + scaling pipeline

        Returns:
            self (for chaining)

        Warnings:
            - Missing `screen` will make sprite invisible (except UI team)
            - Grid conversion after offset may lose precision
        """

        # Check if a screen has been assigned (doesn't apply to ui sprites as they render on an independent layer)
        if not screen and (not hasattr(self, 'team') or self.team != "ui"):
            print(f"⚠️  No `screen` arg has been passed to {self.__class__.__name__}'s `Summon`, the sprite will not be visible.")


        # --- OFFSET RESOLUTION ---
        # If offsets are provided, use them; otherwise fall back to the object's defaults
        ox = offset_x*config.resolution_scale if offset_x is not None else self.POS_X_OFFSET
        oy = offset_y*config.resolution_scale if offset_y is not None else self.POS_Y_OFFSET

        # --- INPUT RESOLUTION ---
        # Allow EITHER grid coords (row/col) OR pixel coords (pos_x/pos_y)
        if target_pos_x is not None or target_pos_y is not None:
            # Pixel‑based spawn
            self.pos_x = (target_pos_x if target_pos_x is not None else 0) + ox
            self.pos_y = (target_pos_y if target_pos_y is not None else 0) + oy

            # Convert pixel → grid (keeps your original behaviour)
            coord_grid = pixel_to_grid(x=int(self.pos_x), y=int(self.pos_y))
            self.pos_row, self.pos_col = coord_grid["row"], coord_grid["col"]

        else:
            # Grid‑based spawn (your original behaviour)
            coord_pixel = grid_to_pixel(row=target_row, col=target_col)
            self.pos_x = coord_pixel["x"] + ox
            self.pos_y = coord_pixel["y"] + oy

            # From coord_pixel + offsets, translate into pixelspace | LOSES ACCURACY WITH OFFSET
            coord_grid = pixel_to_grid(x=int(self.pos_x), y=int(self.pos_y))
            self.pos_row, self.pos_col = coord_grid["row"], coord_grid["col"]
        
        # Update empty spawn constants
        coord_grid = pixel_to_grid(x=int(self.pos_x), y=int(self.pos_y))
        self.SUMMONED_POS_X, self.SUMMONED_POS_Y = self.pos_x, self.pos_y
        self.SUMMONED_POS_ROW, self.SUMMONED_POS_COL = coord_grid["row"], coord_grid["col"]

        # If a colour was passed, stash it (so future animations/rescales reuse it)
        if colour is not None:
            self.surface_tint_colour = tuple(colour)
        
        # Fallback to sprite's index if none
        if initial_sprite_index is None:
            initial_sprite_index = self.sprite_index

        # Use set_sprite to load frame and apply tint/scaling logic consistently
        # NOW RESPECTS THE initial_sprite_index PARAMETER
        try:
            self.set_sprite(0, initial_sprite_index, recolour=self.surface_tint_colour)
        except Exception:
            # fallback if spritesheet not available
            if self.spritesheet and self.spritesheet[0]:
                raw = loadSprite([self.spritesheet[0][initial_sprite_index]])
                self.surface_original = raw.convert_alpha()
                if self.surface_tint_colour is not None:
                    self.surface_tinted_original = self._tint_surface(self.surface_original, self.surface_tint_colour)
                source = self.surface_tinted_original if self.surface_tinted_original else self.surface_original
                self.surface_render = self._build_render_surface(source)

        if self.surface_render:
            self.sprite_rect = self.surface_render.get_rect(topleft=(self.pos_x, self.pos_y))
        else:
            self.sprite_rect = pygame.Rect(self.pos_x, self.pos_y, 0, 0)

        self.screen = screen
        return self

    def respawn(self) -> None:
        """
        Reset sprite to its original summoned position.

        Uses stored pixel coordinates (not grid) to ensure exact placement.
        """
        self.move_position(dx=self.SUMMONED_POS_X,dy=self.SUMMONED_POS_Y,set_position=True)

    #region rescale
    def rescale(self):
        """
        Update sprite when global resolution scale changes.

        Effects:
            - Recomputes pixel position using scale ratio
            - Updates grid coordinates
            - Rebuilds render surface from original (no compounding)

        Important:
            Must be called AFTER `config.resolution_scale` changes.

        Early exit:
            If scale unchanged, does nothing.
        """
        new_scale = config.resolution_scale
        old_scale = config.last_resolution_scale

        if new_scale == old_scale:
            return

        print("Rescaling from", old_scale, "to", new_scale)

        # Compute correct relative ratio
        scale_ratio = new_scale / old_scale

        # Update config tracking
        config.last_resolution_scale = new_scale

        # Update pixel positions based on ratio
        self.pos_x = int(self.pos_x * scale_ratio)
        self.pos_y = int(self.pos_y * scale_ratio)

        # Update grid coords using your existing logic
        coord_grid = pixel_to_grid(int(self.pos_x), int(self.pos_y))
        self.pos_col = coord_grid["col"]
        self.pos_row = coord_grid["row"]

        # Scale surface from ORIGINAL source (tinted-original preferred)
        source_surface = self.surface_tinted_original if self.surface_tinted_original else self.surface_original
        if source_surface is not None:
            self.surface_render = self._build_render_surface(source_surface)

        # Update rect
        if self.sprite_rect and self.surface_render:
            self.sprite_rect.size = self.surface_render.get_size()
            self.sprite_rect.topleft = (self.pos_x, self.pos_y)
        

    #region draw
    def draw(self, screen):
        """
        Render the sprite to the given screen.

        Steps:
            - Sync grid position from pixel coords
            - Update rect position
            - Blit `surface_render`

        No-op if:
            - surface_render is None
        """
        if not self.surface_render:
            return

        # (Integer) Grids
        coord_grid = pixel_to_grid(int(self.pos_x),int(self.pos_y))
        self.pos_col = coord_grid["col"]
        self.pos_row = coord_grid["row"]
        if self.sprite_rect:
            self.sprite_rect.topleft = (self.pos_x, self.pos_y)

        screen.blit(self.surface_render, (self.pos_x, self.pos_y))
    

    #region Spritesheet
    def replace_spritesheet(self, new_spritesheet):
        """
        Replace the sprite's spritesheet and reset animation state.

        Args:
            new_spritesheet: 2D list [animation][frame]

        Effects:
            - Resets oscillator
            - Reloads first frame via `set_sprite`
            - Preserves current tint (if any)
        """
        self.spritesheet = new_spritesheet
        # reset oscillator and surfaces
        self._sprite_oscillator = 0
        # reload initial frame using set_sprite to keep tint behaviour consistent
        self.set_sprite(0, 0, recolour=self.surface_tint_colour)
    
    def set_sprite(self, anim_index: int, frame_index: int, recolour: tuple[int,int,int] | None = None):
        """
        Load and apply a specific sprite frame.

        Args:
            anim_index: Animation row
            frame_index: Frame within animation
            recolour: Optional tint override

        Pipeline:
            1. Load raw image → surface_original
            2. Apply tint (if set)
            3. Scale → surface_render
            4. Update rect size

        Guarantees:
            - Always rebuilds from raw source (no stacking artifacts)
        """
        # Update tint colour if recolour explicitly provided
        if recolour is not None:
            self.surface_tint_colour = tuple(recolour)

        # Load raw frame
        raw = loadSprite([self.spritesheet[anim_index][frame_index]])
        self.surface_original = raw.convert_alpha()

        # If a tint colour exists, produce a tinted original; else clear it
        if self.surface_tint_colour is not None:
            self.surface_tinted_original = self._tint_surface(self.surface_original, self.surface_tint_colour)
            source = self.surface_tinted_original
        else:
            self.surface_tinted_original = None
            source = self.surface_original

        # Scale to current global * per-sprite scale
        self.surface_render = self._build_render_surface(source)

        if self.sprite_rect and self.surface_render:
            self.sprite_rect.size = self.surface_render.get_size()

    def oscillate_sprite(self, oscillator_override: int | None = None):
        """
        Advance (or set) animation frame within the current spritesheet.

        Args:
            oscillator_override: Explicit frame index (wraps safely)

        Behavior:
            - Cycles through frames in animation[0]
            - Reloads frame and reapplies tint
            - Rebuilds render surface

        Raises:
            AssertionError if no frames exist.
        """
        assert len(self.spritesheet[0]) > 0, "[oscillate_sprite] No frames available in spritesheet!"

        if oscillator_override is not None:
            self._sprite_oscillator = oscillator_override % len(self.spritesheet[0])
        else:
            self._sprite_oscillator = (self._sprite_oscillator + 1) % len(self.spritesheet[0])

        anim_index = 0
        frame_index = self._sprite_oscillator
        # Load new base frame and apply current tint (if any)
        raw = loadSprite([self.spritesheet[anim_index][frame_index]])
        self.surface_original = raw.convert_alpha()

        # Reapply tint cache if we have tint_colour
        if self.surface_tint_colour is not None:
            self.surface_tinted_original = self._tint_surface(self.surface_original, self.surface_tint_colour)
            source = self.surface_tinted_original
        else:
            self.surface_tinted_original = None
            source = self.surface_original

        self.surface_render = self._build_render_surface(source)
        if self.sprite_rect and self.surface_render:
            self.sprite_rect.size = self.surface_render.get_size()

    #region Positioning
    def move_position(self, dx=0, dy=0, drow=0, dcol=0, set_position=False):
        """
        Move or set sprite position.

        Args:
            dx, dy: Pixel movement (pre-scale unless set_position=True)
            drow, dcol: Grid movement (converted to pixels)
            set_position: If True, directly sets absolute pixel position

        Behavior:
            - Grid movement is converted using CELL_SIZE
            - Movement is scaled by resolution_scale
            - Updates grid coordinates + rect

        Notes:
            - `set_position=True` expects already-scaled pixel values
        """

        # Convert row/col movement to pixel movement (unscaled)
        cell = config.CELL_SIZE
        if drow or dcol:
            dx, dy = dcol * cell, drow * cell

        # __SCALE MOVEMENT TO MATCH RENDER __SCALE
        scale = config.resolution_scale
        
        if set_position:
            # DIRECTLY SET POSITION (resolution_scale already applied)
            self.pos_x = dx
            self.pos_y = dy
        else:
            # APPLY SCALING BASED ON RESOLUTION
            dx *= scale
            dy *= scale
            # APPLY MOVEMENT
            self.pos_x += dx
            self.pos_y += dy

        # Update grid coords
        grid = pixel_to_grid(x=self.pos_x, y=self.pos_y)
        self.pos_row, self.pos_col = grid["row"], grid["col"]

        if self.sprite_rect:
            self.sprite_rect.topleft = (self.pos_x, self.pos_y)



    
    #region Tasking
    def ticker(self):
        """
        Increment internal tick counter.

        Typically called once per frame.
        """
        self.tick += 1
    
    def is_off_screen(self):
        """
        Check whether sprite is outside the playable grid bounds.

        Returns:
            True if outside configured grid limits, else False.
        """
        beyond_max_col = self.pos_col >= config.MAX_COL
        beyond_min_col = self.pos_col < -1
        beyond_max_row = self.pos_row >= config.MAX_ROW
        beyond_min_row = self.pos_row < -1
        
        return beyond_max_col or beyond_min_col or beyond_max_row or beyond_min_row
    
    def is_on_screen_edge(self):
        """
        Check whether sprite is at the edge of the screen.

        Returns:
            True if at the edge, else False.
        """
        beyond_max_col = self.pos_col >= config.MAX_COL - 1
        beyond_min_col = self.pos_col <= -1
        beyond_max_row = self.pos_row >= config.MAX_ROW - 1
        beyond_min_row = self.pos_row < 0
        
        return beyond_max_col or beyond_min_col or beyond_max_row or beyond_min_row

    def task(self):
        pass

    def task_upon_click(self):
        pass





#region -> SPRITES





#region Cursor
class Cursor(Sprite):
    def __init__(self):
        super().__init__()
        self.spritesheet = [[sprites_dir / "cursor.png",
                             sprites_dir / "cursor_click.png"]]
        

#region Cell
class Cell(Sprite):
    def __init__(self):
        super().__init__()
        self.spritesheet = [[sprites_dir / "cell.png"]]


#region MissingCell
class MissingCell(Sprite):
    def __init__(self):
        super().__init__()
        self.spritesheet = [[sprites_dir / "missing.png"]]





#region Dog
class Dog(Sprite):
    def __init__(self):
        super().__init__()
        self.spritesheet = [[actor_dir / "dog.png"]]
        self.team = "actors"
        self.direction_x, self.direction_y = 1, 0
        self.speed = 1
    
    def task(self):
        if self.tick % (config.frame_rate * 300) == 0: # // Every 300 seconds, random chance to drop
            if randint(1, 100) == 1:
                self.mark_to_drop = True

        if self.tick % 30 == 0: # // Every 30 frames, change direction randomly
            self.direction_x = randint(-1, 1)
            self.direction_y = randint(-1, 1)

        if self.tick % 1 == 0: # // Every 6 frames, move
            if self.is_off_screen():
                self.direction_x *= -1 # // Reverse direction if we're about to go off-screen
                self.direction_y *= -1 # // Reverse direction if we're about to go off-screen
            self.move_position(dx=self.direction_x*self.speed, dy=self.direction_y*self.speed)
    
    def task_upon_click(self):
        self.speed += 1
        print(f"Dog speed increased to {self.speed}!")


class Browning(Sprite):
    def __init__(self):
        super().__init__()
        self.spritesheet = [[object_dir / "brown.png"]]
        self.team = "decor"






#region Particle
class Particle(Sprite):
    """
    Lightweight transient sprite with a finite lifetime.

    Attributes:
        lifetime: Remaining frames before deletion

    Behavior:
        - Call `decay()` each frame
        - Marks itself for deletion when lifetime expires
    """
    def __init__(self):
        super().__init__()
        self.spritesheet = [[sprites_dir / "missing.png"]]
        self.lifetime = 3 * config.frame_rate  # frames
    
    def decay(self):
        """
        Decrement lifetime and mark for deletion when expired.
        """
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.mark_for_deletion = True


class Confetti(Particle):
    """
    Decorative particle with randomized appearance and motion.

    Features:
        - Random sprite variation
        - Random positional offset
        - Procedural colour tint
        - Downward drift with horizontal jitter

    Lifecycle:
        - Initializes position from external source (e.g. ball impact)
        - Applies drift each frame
        - Self-deletes via Particle.decay()
    """
    def __init__(self):
        super().__init__()
        self.team = "particles"

        variation = randint(1,2)
        self.spritesheet = [[sprites_dir / "particle" / f"confetti{variation}.png"]]

        # Random offset
        self.POS_X_OFFSET = randint(-4, 4)
        self.POS_Y_OFFSET = randint(-4, 4)

        # Fall origin
        self._fall_origin_x = self.pos_x
        self._fall_origin_y = self.pos_y

        # Dominant Colour
        white_dominant = (randint(0,2) == 1)
        colour_values = [255, randint(50, 100), randint(50, 100)] if not white_dominant else [255,255,255]
        random.shuffle(colour_values)
        self.set_sprite(0, 0, recolour=tuple(colour_values))
        
        self._position_initialized = False

    def task(self):
        super().task()