import os
import sys
from pathlib import Path

class Resource:
    def set_app_name(self, app_name: str):
        """
        Sets the application name used by the Resource class.

        This name is critical for determining the correct path when the application
        is packaged (e.g., in a temporary folder).

        Args:
            app_name: The name of the application/game.
        """
        self.app_name = app_name

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
        is_exe = executable.suffix.lower() == ".exe" and executable.name.lower() != "python.exe"
        if frozen or compiled or is_exe:
            temp_root = Path(os.environ["TEMP"]) / self.app_name / "assets"
            print(temp_root / relative)
            return temp_root / relative

        # Development mode
        print(Path(__file__).parent / "assets" / relative)
        return Path(__file__).parent / "assets" / relative
    
resource = Resource()