import pygame

from py_app import app
from math import ceil

class Config:
    # PLEASE DO NOT TOUCH THE SCALE VALUE
    def __init__(self):

        # consts
        self.RES_X_INIT, self.RES_Y_INIT = app.DISP_RES_X_INIT, app.DISP_RES_Y_INIT
        self.RESOLUTION_SCALE_INIT = app.DISP_SCALE
        self.CELL_SIZE = app.DISP_CELL_SIZE   # ALWAYS 8
        self.MAX_COL, self.MAX_ROW = ceil(self.RES_X_INIT / self.CELL_SIZE), ceil(self.RES_Y_INIT / self.CELL_SIZE)
        print(self.MAX_COL,self.MAX_ROW)

        self.resolution_scale = app.DISP_SCALE
        self.last_resolution_scale = app.DISP_SCALE
        self.res_x = self.RES_X_INIT * app.DISP_SCALE
        self.res_y = self.RES_Y_INIT * app.DISP_SCALE
        self.frame_rate = app.DISP_FRAME_RATE
        self.clock = pygame.time.Clock()

        self.volume_multiplier = 1



    def redefine(self, scale=None, framerate=None, clock=None, volume=None):
        """
        Redefines global configuration values (resolution scale, frame rate, etc.).

        If 'scale' is provided, derived resolution values (res_x, res_y) are updated.
        WARNING: This function does NOT mutate `self.last_resolution_scale`.
        Any sprites relying on scale changes must call their own `rescale()` method
        to correctly handle the historical scale state.

        Returns:
            The updated value (scale, framerate, etc.) if the parameter was provided, else None.
        """
        if scale is not None:
            # Store previous scale (left intact for sprites until they rescale)
            old = self.resolution_scale

            # Update derived values
            self.resolution_scale = scale
            self.res_x = self.RES_X_INIT * scale
            self.res_y = self.RES_Y_INIT * scale

            # Optional: return tuple(old, new) so caller may trigger rescale on sprites
            return scale
        if framerate is not None:
            self.frame_rate = framerate
            return framerate
        if clock is not None:
            self.clock = clock
            return clock
        if volume is not None:
            self.volume_multiplier = volume
    
    def calculate_scale_against_pc_resolution(self, scale_increment=0, desktop_res_x=None, desktop_res_y=None) -> int:
        """
        Calculates the next valid scale increment, clamping the result between 1 and 
        the maximum scale that fits the given PC resolution.

        This function enforces boundary checks:
        - If increasing scale exceeds the maximum fit, it resets to scale 1.
        - If decreasing scale falls below 1, it resets to the maximum fit scale.

        Returns:
            The next valid scale factor, or the max scale if a boundary is hit.
        """

        # Find the maximum scale that fits within the PC resolution
        max_scale_x = desktop_res_x // self.RES_X_INIT
        max_scale_y = desktop_res_y // self.RES_Y_INIT
        max_scale = min(max_scale_x, max_scale_y)

        # Increment scale
        next_scale = self.resolution_scale + scale_increment
        
        
        # Wrap around logic
        if scale_increment > 0 and next_scale > max_scale:
            return 1
        elif scale_increment < 0 and next_scale < 1:
            return max_scale
        
        return next_scale

    def calculate_best_fit_scale(self, desktop_res_x, desktop_res_y) -> int:
        """
        Calculates a stable, intermediate scale factor (best fit) for the given 
        desktop resolution.

        The scale is determined by finding the maximum possible fit scale and then 
        using half of that value, ensuring the resulting scale is at least 1.

        Returns:
            The calculated best fit integer scale factor.
        """

        # Find the maximum scale that fits within the PC resolution
        max_scale_x = desktop_res_x // self.RES_X_INIT
        max_scale_y = desktop_res_y // self.RES_Y_INIT
        max_scale = min(max_scale_x, max_scale_y)
        
        # Use half of the maximum scale for middle-ground sizing
        half_scale = max_scale // 2
        
        # Ensure we have at least scale of 1
        return max(1, half_scale)


# Singleton instance
config = Config()