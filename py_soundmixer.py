import pygame
from py_resource import resource


class SoundMixer:
    """
    Manages and plays multiple sound effects and background music tracks
    using pygame.mixer.

    Initializes the Pygame mixer system, handling resource loading and
    playback controls for various sounds and background music loops.
    """
    def __init__(self, frequency=44100, size=-16, channels=2, buffer=512):
        """
        Initializes the SoundMixer and attempts to set up the Pygame mixer.

        Args:
            frequency: The audio frequency in Hz (default: 44100).
            size: The sample size in bits (default: -16 for signed 16-bit).
            channels: The number of audio channels (default: 2 for stereo).
            buffer: The audio buffer size in samples (default: 512).
        """
        self._initialized = False
        self.sounds = {}   # (name, path) -> Sound
        self._channels = {}  # (name, path) -> Channel
        self._music = None  # (name, path) -> currently loaded music track
        self._paused = set()

        try:
            pygame.mixer.pre_init(frequency, size, channels, buffer)
            pygame.mixer.init()
            self._initialized = True
        except Exception as e:
            print(f"[py_soundmixer] : Failed to initialize mixer: {e}")

    def _load_sound(self, name: str, relative_path: str):
        """
        Loads a reusable sound effect (non-music) into the mixer's sound dictionary.

        Args:
            name: A unique identifier for the sound.
            relative_path: The resource path for the sound file.

        Returns:
            pygame.mixer.Sound or None: The loaded sound object, or None if loading failed.
        """
        path = resource.resource_path(relative_path)

        if not path.exists():
            print(f"[py_soundmixer] : Missing sound file: {path}")
            return None

        key = (name, str(path))

        if key not in self.sounds:
            try:
                self.sounds[key] = pygame.mixer.Sound(str(path))
            except Exception as e:
                print(f"[py_soundmixer] : Failed to load {path}: {e}")
                return None

        return self.sounds[key]

    def _load_music(self, name: str, relative_path: str):
        """
        Locates the file path for music tracks intended for continuous playback.

        Args:
            name: A unique identifier for the music track.
            relative_path: The resource path for the music file.

        Returns:
            tuple[tuple[str, str], Path] or tuple[None, None]:
            A tuple containing the unique key and the absolute path, or (None, None) if failed.
        """
        path = resource.resource_path(relative_path)

        if not path.exists():
            print(f"[py_soundmixer] : Missing music file: {path}")
            return None, None

        key = (name, str(path))
        return key, path

    def play(self, name: str, relative_path: str, vol_mult=1.0, loops=0):
        """
        Plays a sound effect or background music track.

        If `loops` is -1, the sound is treated as long-form music and routed
        through `pygame.mixer.music`. Otherwise, it plays as a normal sound effect.

        Args:
            name: The unique name identifier for the sound/music.
            relative_path: The resource path to the sound/music file.
            vol_mult: The volume multiplier (0.0 to 1.0).
            loops: Number of times to loop (0 for one time, -1 for infinite music).
        """
        if not self._initialized:
            return

        # Long-running infinite loops are more reliable through pygame.mixer.music.
        if loops == -1:
            key, path = self._load_music(name, relative_path)
            if not key:
                return

            try:
                pygame.mixer.music.load(str(path))
                pygame.mixer.music.set_volume(max(0.0, min(1.0, vol_mult)))
                pygame.mixer.music.play(loops=-1)
                self._music = key
                self._paused.discard(key)
            except Exception as e:
                print(f"[py_soundmixer] : Failed to play music '{name}': {e}")
            return

        sound = self._load_sound(name, relative_path)
        if not sound:
            return

        sound.set_volume(max(0.0, min(1.0, vol_mult)))

        try:
            channel = sound.play(loops=loops)
            if channel:
                key = (name, str(resource.resource_path(relative_path)))
                self._channels[key] = channel
        except Exception as e:
            print(f"[py_soundmixer] : Failed to play '{name}': {e}")

    def pause(self, name: str, unpause_only: bool = False, pause_only: bool = False):
        """
        Pauses or unpauses a specific sound or music track.

        This method handles pausing individual sound channels and the continuous
        `pygame.mixer.music` track separately.

        Args:
            name: The name identifier of the sound or music track to control.
            unpause_only: If True, only unpauses (and ignores if currently paused).
            pause_only: If True, only pauses (and ignores if currently playing).
        """
        if not hasattr(self, "_paused"):
            self._paused = set()

        # Handle pygame.mixer.music separately, since it is not a normal channel.
        if self._music and self._music[0] == name:
            key = self._music

            if key in self._paused:
                if pause_only:
                    return
                pygame.mixer.music.unpause()
                self._paused.remove(key)
            elif not unpause_only:
                pygame.mixer.music.pause()
                self._paused.add(key)
            return

        for key, channel in list(self._channels.items()):
            if key[0] != name:
                continue

            if key in self._paused:
                if pause_only:
                    continue
                channel.unpause()
                self._paused.remove(key)
            elif not unpause_only:
                channel.pause()
                self._paused.add(key)

    def stop(self, name: str):
        """
        Stops a specific sound effect or music track immediately.

        Stops the underlying channel/music stream and removes the reference.

        Args:
            name: The name identifier of the sound or music track to stop.
        """
        if self._music and self._music[0] == name:
            pygame.mixer.music.stop()
            self._paused.discard(self._music)
            self._music = None
            return

        for key, channel in list(self._channels.items()):
            if key[0] == name:
                channel.stop()
                self._channels.pop(key, None)

    def stop_all(self):
        """
        Stops all currently playing sounds and music tracks, and clears internal state.
        """
        pygame.mixer.music.stop()
        pygame.mixer.stop()
        self._channels.clear()
        self._paused.clear()
        self._music = None

    def quit(self):
        """
        Uninitializes the Pygame mixer subsystem.
        Should be called when the application exits.
        """
        pygame.mixer.quit()
        self._initialized = False


soundMixer = SoundMixer()