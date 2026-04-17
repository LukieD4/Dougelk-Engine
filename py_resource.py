import os
import sys
from pathlib import Path

class Resource:
    def __init__(self):
        self.app_name = None
        self.__exe_enable_spoof = None

    def set_app_name(self, app_name: str):
        """
        Sets the application name used by the Resource class.

        This name is critical for determining the correct path when the application
        is packaged (e.g., in a temporary folder).

        Args:
            app_name: The name of the application/game.
        """
        self.app_name = app_name
    
    def _set_exe_spoof(self, enabled: bool):
        """
        (DEV USE ONLY) Sets an environment variable to spoof the executable path.

        This is a development tool to simulate the conditions of running as an executable
        without actually packaging the application. It can help identify issues related
        to resource paths and version file handling during development.

        Args:
            enabled: If True, sets the spoof; if False, removes it.
        """
        self.__exe_enable_spoof = enabled
        return enabled

    def resource_path(self, relative: str) -> Path:
        """
        Determines the correct file system path for a given relative resource.

        The logic automatically switches between two modes:
        1. Development Mode: Uses the directory adjacent to the current file (`__file__`).
        2. Deployment/Frozen Mode: Uses the system's temporary directory (%TEMP%)
        to ensure resources are found when packaged (e.g., via PyInstaller or Nuitka).

        Args:
            relative: The path or filename relative to the assets directory (e.g., "images/player.png").

        Returns:
            Path: The absolute Path object pointing to the resource location.
        """

        # Detect "running as an EXE" in ALL Nuitka modes:
        # - python.exe inside temp (Python-Onefile mode)
        # - frozen EXE (future)
        # - stub EXE
        frozen = getattr(sys, "frozen", False)
        compiled = "__compiled__" in globals()
        executable = Path(sys.executable)
        __exe_spoof = Path(os.environ["TEMP"]) / self.app_name / f"{self.app_name}.exe" if self.__exe_enable_spoof else None
        is_exe = executable.suffix.lower() == ".exe" and executable.name.lower() != "python.exe"
        if frozen or compiled or is_exe or __exe_spoof:
            temp_root = Path(os.environ["TEMP"]) / self.app_name
            print_output = f"[py_resource] : resource_path : {temp_root / relative}"
            print_output += "__exe_spoof IS USED\n‼️‼️You may see symptoms: - Game failing to start - Resources not found - Version file not updating" if __exe_spoof else ""
            print(print_output)
            return temp_root / relative

        # Development mode
        print(f"[py_resource] : resource_path : {Path(__file__).parent / relative}")
        return Path(__file__).parent / relative
    
resource = Resource()