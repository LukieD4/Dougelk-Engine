import pygame, threading, asyncio
from pygame import joystick
from py_render import pixel_to_grid

# Using Xbox's scheme!
DEFAULT_CONTROLLER_BUTTON_MAP = {
    "a": 0,
    "b": 1,
    "x": 2,
    "y": 3,
    "lb": 4,
    "rb": 5,
    "back": 6,
    "start": 7,
    "dpad_up": 11,
    "dpad_down": 12,
    "dpad_left": 13,
    "dpad_right": 14,
}

# Thumbstick direction mappings
THUMBSTICK_DIRECTIONS = {
    "up": ("_y", "up"),
    "down": ("_y", "down"),
    "left": ("_x", "left"),
    "right": ("_x", "right"),
}

THUMBSTICK_SIDES = ["left", "right"]

# Build CROSS_PLATFORM_SPRITE_MAP automatically
CROSS_PLATFORM_SPRITE_MAP = {
    "XBOX": {
        "a": "xbx_a",
        "b": "xbx_b",
        "x": "xbx_x",
        "y": "xbx_y",
        "lb": "xbx_lb",
        "rb": "xbx_rb",
        "back": "xbx_back",
        "start": "xbx_start",
    },
    "DUALSHOCK": {
        "a": "psn_cross",
        "b": "psn_circle",
        "x": "psn_square",
        "y": "psn_triangle",
        "lb": "psn_l2",
        "rb": "psn_r2",
        "back": "psn_back",
        "start": "psn_select",
    },
}
# Add thumbstick mappings
# // All valid entries will be like "left_x_up": "LeftTS_U" or "right_y_down": "RightTS_D", etc.
for family, sprites in CROSS_PLATFORM_SPRITE_MAP.items():
    for side in THUMBSTICK_SIDES:
        for direction, (axis_suffix, dir_name) in THUMBSTICK_DIRECTIONS.items():
            key = f"{side}{axis_suffix}_{direction}"
            prefix = "LeftTS" if side == "left" else "RightTS"
            suffix = {"up": "U", "down": "D", "left": "L", "right": "R"}[direction]
            sprites[key] = f"{prefix}_{suffix}"
    sprites["left_press"] = "LeftTS_P"
    sprites["right_press"] = "RightTS_P"

CONTROLLER_AXIS_MAP = {
    "left_x": 0,
    "left_y": 1,
    "right_x": 2,
    "right_y": 3,
}




#region InputManager
class InputManager:
    
    def __init__(self):
        self.mode = None  # updated externally in client.py main loop.
        self.mode_old = None
        self.debug = False  # updated externally in client.py main loop.

        # Mouse tracking
        self.mouse_object = None
        self.mouse_pos_x, self.mouse_pos_y = 0, 0
        self.mouse_pos_row, self.mouse_pos_col = 0, 0

        # Input method tracking
        self.current_input_method = ""
        self.last_input_method = "Default" # Default: Keyboard & Mouse, "Xbox Series X Controller": Controller
        
        # Detect controllers
        pygame.joystick.init()
        self.controller_thread = None
        self.controllers = []
    
    #region Mouse
    def initialise_cursor(self, cursor_object, screen):
        """
        Initializes and summons the mouse cursor object on the screen.

        Args:
            cursor_object: The instantiated cursor object (e.g., from py_render).
            screen: The Pygame screen surface.

        Returns:
            The configured cursor object.
        """
        self.mouse_object = cursor_object.summon(target_row=self.mouse_pos_row, target_col=self.mouse_pos_col,screen=screen)
        return self.mouse_object
    
    def update_mouse_positioning_attributes(self, mouse_position) -> None:
        """
        Updates the internal attributes tracking the mouse's current position 
        (in pixels and then converted to grid coordinates).

        Args:
            mouse_position (tuple): A tuple (x, y) representing the mouse position in pixels.
        """
        self.mouse_pos_x, self.mouse_pos_y = mouse_position[0], mouse_position[1]
        grid_space = pixel_to_grid(self.mouse_pos_x, self.mouse_pos_y)
        self.mouse_pos_row, self.mouse_pos_col = grid_space["row"], grid_space["col"]

    def update_mouse_input_state(self, event):
        """
        Processes pygame mouse events (down/up) to update the input state
        and potentially change the cursor's appearance.

        Args:
            event (pygame.event.Event): The mouse event.

        Returns:
            The event type (e.g., pygame.MOUSEBUTTONDOWN) if a key input occurred, 
            otherwise None.
        """
        if event.type == pygame.MOUSEBUTTONDOWN:
            print(f"py_input : update_mouse_input_state (DOWN) : {event.pos}")
            self.update_mouse_positioning_attributes(event.pos)
            self.mouse_object.set_sprite(0,1)
            return pygame.MOUSEBUTTONDOWN
        elif event.type == pygame.MOUSEBUTTONUP:
            print(f"py_input : update_mouse_input_state (UP) : {event.pos}")
            self.update_mouse_positioning_attributes(event.pos)
            self.mouse_object.set_sprite(0,0)
            return pygame.MOUSEBUTTONUP
            
    #region Last Input
    def resolve_active_input_method(self, event):
        """
        Determines if the current input event suggests a change in the primary 
        input method (e.g., switching from keyboard to controller).

        Args:
            event (pygame.event.Event): The detected pygame event.

        Returns:
            tuple[str, str]: A tuple containing (last_input_method, current_input_method).
        """
        current_input_method = self.current_input_method

        if (event.type == pygame.KEYDOWN) or event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
            self.last_input_method = "Default"
            self.current_input_method = "Default"

        elif event.type in (pygame.JOYBUTTONDOWN, pygame.JOYHATMOTION):
            if self.controllers:
                self.last_input_method = self.controllers[0].get_name()
                self.current_input_method = self.controllers[0].get_name()

        elif event.type == pygame.JOYAXISMOTION:
            if abs(event.value) > 0.5 and self.controllers:
                self.last_input_method = self.controllers[0].get_name()
                self.current_input_method = self.controllers[0].get_name()
        
        return self.last_input_method, current_input_method

    #region Controller
    def get_controller_family(self):
        """
        Analyzes the last active input method to determine the controller family 
        (e.g., "XBOX" or "DUALSHOCK").

        Returns:
            str | None: The detected controller family name, or None if using default input.
        """
        if self.last_input_method == "Default":
            return None

        name = self.last_input_method.lower()
        # name = "sony"

        if "xbox" in name:
            return "XBOX"

        if ("dualshock" in name or 
            "dual sense" in name or 
            "dualsense" in name or 
            "sony" in name or 
            "wireless controller" in name):
            return "DUALSHOCK"

        return "XBOX"  # fallback for generic controllers
    
    def get_latest_controllers(self):
        """
        Scans all connected joystick devices and initializes them. 
        This function is designed to run in a separate thread.
        """
        while True:
            self.controllers = [
                pygame.joystick.Joystick(i)
                for i in range(pygame.joystick.get_count())
            ]
            for c in self.controllers:
                c.init()

            pygame.time.wait(500)

    #region Sprite resolver 
    def get_sprite_for_keyboard_key(self, keyboard_key):
        """
        Translates a keyboard input string into the corresponding controller 
        sprite name for the active platform (XBOX/DUALSHOCK).

        It handles both traditional button/axis mappings and direct thumbstick inputs.

        Args:
            keyboard_key (str): The string representation of the keyboard key.

        Returns:
            str | None: The resource name for the controller sprite, or None if no match is found.
        """
        if self.last_input_method == "Default":
            return None

        k = keyboard_key.lower()

        # Direct thumbstick mapping (bypass INPUT_MODES dependency)
        # e.g. 'ltsd' -> 'left_y_down' -> CROSS_PLATFORM_SPRITE_MAP[...] -> 'LeftTS_D' -> +.png
        if k.startswith("lts") or k.startswith("rts"):
            side = "left" if k.startswith("lts") else "right"
            # Extract direction from thumbstick key (e.g., 'leftthumbup' -> 'up')
            direction = k.replace(f"{side}thumb", "")[-1]
            
            match direction:
                case "u":
                    mapped = f"{side}_y_up"
                case "d":
                    mapped = f"{side}_y_down"
                case "l":
                    mapped = f"{side}_x_left"
                case "r":
                    mapped = f"{side}_x_right"
                case "p":
                    mapped = f"{side}_press"
                case _:
                    mapped = None

            if mapped:
                family = self.get_controller_family()
                if family is None:
                    return None
                return CROSS_PLATFORM_SPRITE_MAP[family].get(mapped)

        # Fallback: existing logic (buttons / other keys)
        button = self.translate_keyboard_key_to_controller_key(keyboard_key)
        if button is None:
            return None

        if isinstance(button, tuple):
            axis, threshold, direction = button
            button = f"{axis}_{direction}"

        family = self.get_controller_family()
        if family is None:
            return None

        return CROSS_PLATFORM_SPRITE_MAP[family].get(button)

    def translate_keyboard_key_to_controller_key(self, keyboard_key:str):
        """
        Maps a keyboard key input to a standardized controller key/button name 
        based on the currently active input mode (self.mode).

        Args:
            keyboard_key (str): The keyboard key to translate.

        Returns:
            any | None: The corresponding controller key representation (string or tuple), 
                        or None if no match is found.
        """
        if self.mode not in INPUT_MODES:
            return None
        
        # Santise to PyGame formatting
        keyboard_key = keyboard_key.upper() if len(keyboard_key) > 1 else keyboard_key.lower()
        key_input_is_thumbstick = "THUMB" in keyboard_key
        if not key_input_is_thumbstick: # thumbsticks get unique naming convention
            keyboard_key = f"K_{keyboard_key}" if not keyboard_key.startswith("K_") else keyboard_key


        mode_map = INPUT_MODES[self.mode]

        for action_name, key_list in mode_map.items():

            if (keyboard_key not in key_list) and not key_input_is_thumbstick:
                continue

            for key in key_list:

                if callable(key) and hasattr(key, "__closure__") and key.__closure__:
                    
                    axis = threshold = direction = None
                    for cell in key.__closure__:
                        val = cell.cell_contents
                        if isinstance(val, str) and val in DEFAULT_CONTROLLER_BUTTON_MAP:
                            return val
                        
                else:
                    continue

            return None

        return None



    
    #region Actions    
    def get_action(self, action_name, keys):
        """
        Checks if a specific action (e.g., 'up', 'select') is currently active 
        by checking all associated keys in the current input mode.

        Args:
            action_name (str): The name of the action to check.
            keys (pygame.key.get_pressed): A Pygame event object representing the current key state.

        Returns:
            bool: True if the action is active, False otherwise.
        """
        if self.mode not in INPUT_MODES:
            print(f"⚠️  InputManager: INPUT_MODES couldn't find a matching mode for '{self.mode}'")
            return False

        key_list = INPUT_MODES[self.mode].get(action_name, [])

        for key in key_list:
            if isinstance(key, str):
                key_const = getattr(pygame, key, None)
                if key_const is not None and keys[key_const]:
                    return True

            elif callable(key):
                if key():
                    return True

        return False

    def get_debug_action(self, debug_action_name, keys):
        """
        Checks if a specific debug action is currently active, using the 
        DEBUG_INPUT_MODES mapping.

        Args:
            debug_action_name (str): The name of the debug action to check.
            keys (pygame.key.get_pressed): A Pygame event object representing the current key state.

        Returns:
            bool: True if the debug action is active, False otherwise.
        """
        if self.mode not in INPUT_MODES:
            if self.mode_old == self.mode:
                self.mode_old = self.mode
                print(f"[🧿]  InputManager: DEBUG_INPUT_MODES couldn't find a matching mode for '{self.mode}'")
            return False

        try:
            key_list = DEBUG_INPUT_MODES[self.mode].get(debug_action_name, [])
        except:
            # print("py_input.py : get_debug_action : no `DEBUG_INPUT_MODES` available for `self.mode`")
            return

        for key in key_list:
            if isinstance(key, str):
                key_const = getattr(pygame, key, None)
                if key_const is not None and keys[key_const]:
                    return True

            elif callable(key):
                if key():
                    return True

        return False
    
    #region Static methods
    @staticmethod
    def universal_back():
        """
        Returns a list of input checks that represent a universal 'Back' action, 
        covering keyboard, controller buttons, and DPad movement.
        """
        return ["K_ESCAPE", "K_BACKSPACE", InputManager.controller_button("b"), InputManager.controller_button("back")]
    
    @staticmethod
    def universal_select():
        """
        Returns a list of input checks that represent a universal 'Select/Confirm' action, 
        covering keyboard, controller buttons, and start buttons.
        """
        return ["K_RETURN", "K_SPACE", InputManager.controller_button("a"), InputManager.controller_button("start")]
    
    @staticmethod
    def controller_button(button_name):
        """
        Returns a callable function (a lambda) that checks if a specific 
        controller button or DPad direction is currently pressed on any connected joystick.

        Args:
            button_name (str): The internal button name (e.g., "a", "dpad_up").

        Returns:
            callable: A function that returns True if the button is pressed, False otherwise.
        """
        def check_button():
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)

                if button_name in DEFAULT_CONTROLLER_BUTTON_MAP:
                    btn_index = DEFAULT_CONTROLLER_BUTTON_MAP[button_name]
                    if joy.get_button(btn_index):
                        return True

                if button_name.startswith("dpad_"):
                    hat_x, hat_y = joy.get_hat(0)

                    if button_name == "dpad_up" and hat_y == 1:
                        return True
                    if button_name == "dpad_down" and hat_y == -1:
                        return True
                    if button_name == "dpad_left" and hat_x == -1:
                        return True
                    if button_name == "dpad_right" and hat_x == 1:
                        return True

            return False
        return check_button


    @staticmethod
    def controller_thumbstick(axis=None, threshold=None, direction=None):
        """
        Returns a callable function (a lambda) that checks if a specific 
        thumbstick direction is active (i.e., moved past a threshold) on any connected joystick.

        Args:
            axis (str, optional): The axis name (e.g., "left_y").
            threshold (float, optional): The minimum value magnitude required to register a press.
            direction (str, optional): The required direction ("up", "down", "left", "right").

        Returns:
            callable: A function that returns True if the stick is deflected in the specified direction, False otherwise.
        """
        def check_thumbstick():
            for i in range(pygame.joystick.get_count()):
                joy = pygame.joystick.Joystick(i)
                axis_index = CONTROLLER_AXIS_MAP.get(axis)
                if axis_index is None:
                    continue

                value = joy.get_axis(axis_index)

                if direction == "up" and value < -threshold:
                    return True
                if direction == "down" and value > threshold:
                    return True
                if direction == "left" and value < -threshold:
                    return True
                if direction == "right" and value > threshold:
                    return True

            return False
        return check_thumbstick




# singleton instance
inputManager = InputManager()

inputManager.controller_thread = threading.Thread(
    target=inputManager.get_latest_controllers,
    daemon=True
)
inputManager.controller_thread.start()



#region INPUT_MODES
# Define input modes and their associated key actions
INPUT_MODES = {
    "menu": {
        "up": [
            "K_UP",
            "K_w",
            InputManager.controller_thumbstick(axis="left_y", threshold=0.5, direction="up"),
            InputManager.controller_button("dpad_up"),
        ],
        "down": [
            "K_DOWN",
            "K_s",
            InputManager.controller_thumbstick(axis="left_y", threshold=0.5, direction="down"),
            InputManager.controller_button("dpad_down"),
        ],
        "select": [
            *InputManager.universal_select(),
        ],
        "upscale": [
            "K_i",
            InputManager.controller_button("x")
        ],
        "downscale": [
            "K_o",
            InputManager.controller_button("b")
        ],
        "example1": [
            "K_r",
            InputManager.controller_button("x")
        ],
        "example2": [
            "K_t",
            InputManager.controller_button("y")
        ],
        "example3": [
            "K_u",
            InputManager.controller_button("b")
        ],
    },
}

#region DEBUG_MODES
DEBUG_INPUT_MODES = {
    "menu": {
        "toggle_whole_ui": [
            "K_F1"
        ],
        "toggle_overlay": [
            "K_F2"
        ],
        "unlock_fps": [
            "K_F3"
        ],
        "custom_fps": [
            "K_F4"
        ],
        "custom_fps_impact": [
            "K_F5"
        ],
    },

    "your_new_mode": {
        "tbd": [

        ],
    },

}
