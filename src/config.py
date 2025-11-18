import json
from pathlib import Path
from typing import Tuple

# -----------------------
# GLOBAL CONSTANTS
# -----------------------
WINDOW_WIDTH, WINDOW_HEIGHT = 1920, 1080
GRID_W, GRID_H = 24, 24
CELL_PADDING = 0.05
TICK = 0.16
PREVIEW_TICK = 0.16

# -----------------------
# JOYSTICK CONFIG
# -----------------------
AXIS_DEADZONE = 0.5
BUTTON_ENTER = 0
BUTTON_BACK = 1
BUTTON_PAUSE = 7

# -----------------------
# THEMES
# -----------------------
THEME_COLORS = {
    "Classic Green": {
        "snake": (0.15, 0.95, 0.2, 1.0),
        "apple": (0.95, 0.15, 0.15, 1.0),
        "border": (1.0, 1.0, 1.0, 0.06),
        "title": (1.0, 0.96, 0.51, 1.0),
        "menu_text": (0.7, 0.7, 0.7, 1.0),
        "menu_text_selected": (1.0, 0.96, 0.51, 1.0),
        "menu_highlight_rect": (1.0, 0.9, 0.6, 0.15),
    },
    "Cyberpunk": {
        "snake": (0.0, 0.8, 0.8, 1.0),
        "apple": (1.0, 0.0, 0.9, 1.0),
        "border": (0.2, 0.0, 0.2, 0.15),
        "title": (0.0, 1.0, 1.0, 1.0),
        "menu_text": (0.0, 0.8, 0.8, 1.0),
        "menu_text_selected": (1.0, 0.0, 0.9, 1.0),
        "menu_highlight_rect": (1.0, 0.0, 0.9, 0.25),
    },
    "Monochrome": {
        "snake": (0.7, 0.7, 0.7, 1.0),
        "apple": (1.0, 1.0, 1.0, 1.0),
        "border": (0.2, 0.2, 0.2, 0.1),
        "title": (1.0, 1.0, 1.0, 1.0),
        "menu_text": (0.5, 0.5, 0.5, 1.0),
        "menu_text_selected": (1.0, 1.0, 1.0, 1.0),
        "menu_highlight_rect": (1.0, 1.0, 1.0, 0.15),
    },
}
THEME_NAMES = list(THEME_COLORS.keys())

# -----------------------
# SETTINGS
# -----------------------
RESOLUTIONS = [(1920, 1080)]
DEFAULT_SETTINGS = {
    "vsync": True,
    "bloom": True,
    "use_kawase": False,
    "shake_on_death": True,
    "bloom_strength": 0.9,
    "bloom_radius": 2.0,
    "exposure": 1.0,
    "fullscreen": False,
    "resolution": list(RESOLUTIONS[0]),
    "chroma_enabled": True,
    "chroma_amount": 0.02,
    "chroma_bias": 1.0,
    "color_theme": THEME_NAMES[0],
    "high_score": 0,
}

SETTINGS_FILE = Path(__file__).resolve().parent.parent / "settings.json"


def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
        for k, v in DEFAULT_SETTINGS.items():
            if k not in data:
                data[k] = v
        data["resolution"] = tuple(data["resolution"])
        return data
    except Exception:
        return DEFAULT_SETTINGS.copy()


def save_settings(s):
    try:
        out = dict(s)
        out["resolution"] = list(out["resolution"])
        with open(SETTINGS_FILE, "w") as f:
            json.dump(out, f, indent=2)
    except Exception:
        pass


def to_byte_color(normalized_color: Tuple[float, float, float, float]) -> Tuple[int, int, int]:
    return tuple(int(c * 255) for c in normalized_color[:3])
