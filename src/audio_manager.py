import pygame
from pathlib import Path

class AudioManager:
    def __init__(self):
        self.sounds = {}
        self.base_path = Path(__file__).resolve().parent.parent
        self.audio_dirs = [
            self.base_path / "audio",
            self.base_path / "src" / "audio",
        ]
        self.sfx_volume = 0.5 # Initialize sfx_volume
        self._init_mixer()
        self._load_assets()

    def _init_mixer(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except Exception:
            pass

    def _load_sound(self, filename):
        for d in self.audio_dirs:
            try:
                p = d / filename
                if p.exists():
                    try:
                        return pygame.mixer.Sound(str(p))
                    except Exception:
                        print(f"Sound load failed: {filename}")
                        return None
            except Exception:
                continue
        return None

    def _load_assets(self):
        self.sounds["apple"] = self._load_sound("apple-picked.mp3")
        self.sounds["gameover"] = self._load_sound("game-over.mp3")
        self.sounds["start"] = self._load_sound("start.mp3")
        self.sounds["win"] = self._load_sound("win.mp3")
        self.sounds["select"] = self._load_sound("menu-select.mp3")
        
        self.bg_music_path = self.base_path / "src" / "audio" / "background-music.mp3"

    def play_music(self):
        if not pygame.mixer.get_init():
            return
        try:
            if self.bg_music_path.exists():
                pygame.mixer.music.load(str(self.bg_music_path))
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.5)
        except Exception as e:
            print(f"Error playing music: {e}")

    def set_music_volume(self, volume):
        if not pygame.mixer.get_init():
            return
        try:
            pygame.mixer.music.set_volume(volume)
        except Exception:
            pass

    def set_sfx_volume(self, volume):
        self.sfx_volume = volume

    def play_sound(self, name):
        if not pygame.mixer.get_init():
            return
        if name in self.sounds and self.sounds[name]:
            try:
                self.sounds[name].set_volume(getattr(self, "sfx_volume", 0.5))
                self.sounds[name].play()
            except Exception:
                pass
