import pygame, os, sys

from py_resource import resource

class App:


    def __init__(self):

        # // Basic app info and setup
        self.app_name = "Game"
        resource.set_app_name(self.app_name)
        self.app_authors = ["You!"]
        self.app_description = "A framework build for LukieD4's Space Invaders university project."

        self.filename_gamesettings = f"{self.app_name}.ini"
        self.filename_gamebuildversion = f"{self.filename_gamesettings.split('.')[0]}Build.version"

        self.window_centre(enabled=True) # // Centres the window to the middle of the screen on launch
        self.WINDOWS_ALWAYS_ON_TOP = None # DO NOT CHANGE
        self.window_always_on_top(enabled=True)

        pygame.display.set_caption(self.app_name)

        self.__exe_spoof = resource._set_exe_spoof(enabled=False) # // DEV USE ONLY: Set to True to simulate running as an EXE (useful for testing resource path issues and version file handling during development)


        print(f"App initialized: {self.app_name} by {', '.join(self.app_authors)} - {self.app_description}")



        # // Display configuration
        self.DISP_RES_X_INIT, self.DISP_RES_Y_INIT = 264, 264
        self.DISP_CELL_SIZE = 8   # Rule of thumb: should always be a factor of RES_X_INIT and RES_Y_INIT.
        self.DISP_FRAME_RATE = 60
        self.DISP_SCALE = 2








    @staticmethod
    def window_centre(enabled=True):
        """Utility function to centre the Pygame window on the screen.

        This function sets the SDL environment variable `SDL_VIDEO_CENTERED`
        to ensure the window appears centered upon launch, regardless of the OS.
        """
        os.environ['SDL_VIDEO_CENTERED'] = str(enabled)


    def running_as_exe(self):
        """Checks if the program is currently running as an executable build.

        Returns:
            bool: True if running as a compiled executable (PyInstaller/Nuitka), 
                  False otherwise.
        """

        #// PyInstaller check              // Nuitka check
        if getattr(sys, "frozen", False) or "__compiled__" in globals() or self.__exe_spoof:
            return True

        return False
    

    def window_always_on_top(self, enabled=True):
        """Sets or clears the Pygame window's 'always on top' status (Windows only).

        This function utilizes WinAPI calls (`SetWindowPos`) to place the window
        at the highest layer, keeping it visible above other desktop applications.
        It only executes the necessary winapi code if `enabled` is True.
        """

        if not self.WINDOWS_ALWAYS_ON_TOP:
            self.WINDOWS_ALWAYS_ON_TOP = enabled

        if not enabled:
            return 
    
        try:
            from ctypes import wintypes
            import ctypes
            
            hwnd = pygame.display.get_wm_info()["window"]  # HWND
            user32 = ctypes.WinDLL("user32", use_last_error=True)

            SWP_NOSIZE = 0x0001
            SWP_NOMOVE = 0x0002
            SWP_SHOWWINDOW = 0x0040
            HWND_TOPMOST = -1

            user32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND,
                ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int,
                ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL

            # Keep size/position, just make topmost
            user32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
        except Exception as e:
            print(f"set_always_on_top : WARN : Could not set always on top: {e}")
    
    def build_version_solve(self):
        """Reads the current build version from a file.

        This function is designed to manage the `<Gamename>Build.version` filename, which
        is used to track the build version of the application. It reads the
        version number from the file and returns it as an integer.

        Returns:
            int: The current build version number.
        """
        try:
            with open(resource.resource_path(f"{self.app_name}Build.version")) as f:
                build_version = self.build_version_increment_within_IDE(dev_ignore_exe_check=False)

                if build_version is None:
                    data = f.read().strip()
                    build_version = int(data) if data else 0

                print(f"[py_app] : build_version_solve : Read version from file: {build_version}")
                return int(build_version) if build_version is not None else -1

        except FileNotFoundError:
            print(f"[py_app] : build_version_solve : File not found")
            return -101
        

    def build_version_increment_within_IDE(self, dev_ignore_exe_check=False):
        """
        Reads the current build version from a file, increments it by one,
        and writes the new version number back to the file.

        This function is designed to manage the `Build.version` filename.

        Args:
            dev_ignore_exe_check (bool): If True, bypasses the check for running 
                                      as an executable (useful for testing).

        Returns:
            int: The newly incremented build version number.

        Raises:
            FileNotFoundError: If the version file does not exist and cannot be created.
        """

        if not self.running_as_exe() or dev_ignore_exe_check:
            try:
                with open(self.filename_gamebuildversion, "r+") as f:
                    old = f.read().strip()
                    old_num = int(old) if old else 0
                    new_num = old_num + 1

                    f.seek(0)
                    f.write(str(new_num))
                    f.truncate()

                    return new_num

            except FileNotFoundError:
                with open(self.filename_gamebuildversion, "w") as f:
                    f.write("1")
                    return 1
                
app = App()

if __name__ == "__main__":
    try:
        import subprocess
        # use subprocess.run to execute another Python file
        # [sys.executable] ensures we use the same interpreter that ran py_app.py
        subprocess.run([sys.executable, "py_client.py"], check=True)

    except FileNotFoundError:
        print("\n[FATAL ERROR] py_client.py was not found. Please ensure it is in the same directory.")
    except subprocess.CalledProcessError as e:
        print(f"\n[ERROR] Failed to run py_client.py. The client script might have crashed or exited abnormally. Error: {e}")
    except Exception as e:
        print(f"\n[CRITICAL ERROR] An unexpected error occurred: {e}")

    # Keep the console open so the user can see the output/error message
    print("\n\nProgram finished.")