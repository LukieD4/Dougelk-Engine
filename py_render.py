import pygame
import math

from py_resource import resource
from py_config import config


def recolourSprite(surface: pygame.Surface, new_colour, preserve_alpha=True):
    """
    Tint a surface with new_colour (RGB tuple) while preserving alpha.

    Args:
        surface: The original pygame.Surface to recolor.
        new_colour: The new RGB color tuple (e.g., (255, 0, 0)).
        preserve_alpha: If True, alpha channel is preserved during the tinting process.

    Returns:
        pygame.Surface: The recolored copy of the surface. Returns the original copy if new_colour is None.
    """
    if new_colour is None:
        return surface.copy()

    surf = surface.copy().convert_alpha()

    # Create solid colour surface the same size and blend multiply
    tint = pygame.Surface(surf.get_size(), pygame.SRCALPHA)
    tint.fill((*new_colour, 255))
    surf.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return surf

def loadSprite(spritesheet, pos=(-100, -100)):
    """
    Loads a sprite from a path provided in an iterable.

    If loading fails, it attempts to use 'sprites/missing.png' as a fallback.

    Args:
        spritesheet: An iterable containing the path(s) to the spritesheet.
        pos: (Ignored) Position tuple.

    Returns:
        pygame.Surface: The loaded and alpha-converted sprite surface.
    """
    try:
        path = str(spritesheet[0])
        image = pygame.image.load(path).convert_alpha()
    except Exception as e:
        print(f"[loadSprite] Failed to load {spritesheet[0]}: {e}")
        fallback = resource.resource_path("assets/sprites/missing.png")
        image = pygame.image.load(str(fallback)).convert_alpha()
    return image

def scaleSprite(entity, surface, factor, smooth=False):
    """
    Scales a pygame.Surface by the given factor.

    The minimum resulting size is kept at 1x1.

    Args:
        entity: Placeholder object used for compatibility (e.g., setting entity.scale).
        surface: The source pygame.Surface to scale.
        factor: The scaling factor (float).
        smooth: If True, uses smoothscaling; otherwise, uses standard scaling.

    Returns:
        pygame.Surface: The scaled version of the surface.
    """
    w, h = surface.get_size()
    new_size = (max(1, int(w * factor)), max(1, int(h * factor)))
    # Keep entity.scale for compatibility (existing code expects it)
    try:
        # entity.scale = factor
        pass
    except Exception:
        # entity may be a plain placeholder; ignore if setting fails
        pass
    return pygame.transform.smoothscale(surface, new_size) if smooth else pygame.transform.scale(surface, new_size)

# Grid/pixel helpers
def grid_to_pixel(row=None, col=None):
    """
    Converts coordinates from conceptual grid space (row, col) to screen pixel space.

    Args:
        row: The desired row index (int). Defaults to None.
        col: The desired column index (int). Defaults to None.

    Returns:
        dict: A dictionary containing the calculated 'x' and 'y' pixel coordinates.
    """
    x = col * config.CELL_SIZE * config.resolution_scale if col is not None else None
    y = row * config.CELL_SIZE * config.resolution_scale if row is not None else None
    return {"x": x, "y": y}


def pixel_to_grid(x=None, y=None): # integers
    """
    Converts screen pixel coordinates (x, y) to conceptual grid space (row, col).

    Args:
        x: The input x pixel coordinate (int). Defaults to None.
        y: The input y pixel coordinate (int). Defaults to None.

    Returns:
        dict: A dictionary containing the calculated 'row' and 'col' indices.

    Raises:
        ArithmeticError: If x or y are not integers.
    """
    col = math.floor(x / (config.CELL_SIZE * config.resolution_scale))
    row = math.floor(y / (config.CELL_SIZE * config.resolution_scale))

    if type(col) is float or type(row) is float:
        raise ArithmeticError("Must cast `int(pos_x),int(pos_y)`")

    return {"row": row, "col": col}