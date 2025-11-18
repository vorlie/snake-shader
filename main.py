import random
import sys
import json
import math
from pathlib import Path
from typing import Tuple

import pygame
import moderngl

from src.game import Snake
from src.renderer import Renderer

# Config
WINDOW_WIDTH, WINDOW_HEIGHT = 1920, 1080
GRID_W, GRID_H = 24, 24
CELL_PADDING = 0.05
TICK = 0.16

pygame.init()

try:
    pygame.mixer.init()
except Exception:
    pass

# paths
_base_path = Path(__file__).resolve().parent
_audio_dirs = [
    _base_path / "audio",
    _base_path / "src" / "audio",
]


def _load_sound(filename):
    for d in _audio_dirs:
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


snd_apple = _load_sound("apple-picked.mp3")
snd_gameover = _load_sound("game-over.mp3")
snd_start = _load_sound("start.mp3")
snd_win = _load_sound("win.mp3")
snd_select = _load_sound("menu-select.mp3")

bg_music_path = _base_path / "src" / "audio" / "background-music.mp3"

screen = pygame.display.set_mode(
    (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.OPENGL | pygame.DOUBLEBUF
)
pygame.display.set_caption("Snake Shader v1.0.0")
ctx = moderngl.create_context()
ctx.enable(moderngl.BLEND)
ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

renderer = Renderer(
    ctx, GRID_W, GRID_H, CELL_PADDING, screen_size=(WINDOW_WIDTH, WINDOW_HEIGHT)
)
snake = Snake(GRID_W, GRID_H)
preview_snake = Snake(GRID_W, GRID_H)

global acc, is_transitioning
clock = pygame.time.Clock()
acc = 0.0
running = True
is_transitioning = False
# UI / state
state = "menu"  # menu, settings, playing, gameover
fullscreen = False

# -----------------------
# SETTINGS + PERSISTENCE
# -----------------------

THEME_COLORS = {
    "Classic Green": {
        "snake": (0.15, 0.95, 0.2, 1.0),  # Bright Green
        "apple": (0.95, 0.15, 0.15, 1.0),  # Bright Red
        "border": (1.0, 1.0, 1.0, 0.06),  # White (dim)
        "title": (1.0, 0.96, 0.51, 1.0),  # Yellowish
        "menu_text": (0.7, 0.7, 0.7, 1.0),  # Light Gray (Unselected Text)
        "menu_text_selected": (1.0, 0.96, 0.51, 1.0),  # Yellowish (Selected Text)
        "menu_highlight_rect": (
            1.0,
            0.9,
            0.6,
            0.15,
        ),  # Yellowish Transparent (Selection Bar)
    },
    "Cyberpunk": {
        "snake": (0.0, 0.8, 0.8, 1.0),  # Cyan
        "apple": (1.0, 0.0, 0.9, 1.0),  # Pink/Magenta
        "border": (0.2, 0.0, 0.2, 0.15),  # Dark Purple
        "title": (0.0, 1.0, 1.0, 1.0),  # Cyan
        "menu_text": (0.0, 0.8, 0.8, 1.0),  # Cyan (Unselected Text)
        "menu_text_selected": (1.0, 0.0, 0.9, 1.0),  # Pink (Selected Text)
        "menu_highlight_rect": (
            1.0,
            0.0,
            0.9,
            0.25,
        ),  # Pink Transparent (Selection Bar)
    },
    "Monochrome": {
        "snake": (0.7, 0.7, 0.7, 1.0),  # Light Gray
        "apple": (1.0, 1.0, 1.0, 1.0),  # White
        "border": (0.2, 0.2, 0.2, 0.1),  # Dark Gray
        "title": (1.0, 1.0, 1.0, 1.0),  # White
        "menu_text": (0.5, 0.5, 0.5, 1.0),  # Mid Gray (Unselected Text)
        "menu_text_selected": (1.0, 1.0, 1.0, 1.0),  # White (Selected Text)
        "menu_highlight_rect": (
            1.0,
            1.0,
            1.0,
            0.15,
        ),  # White Transparent (Selection Bar)
    },
}
THEME_NAMES = list(THEME_COLORS.keys())

SETTINGS_FILE = Path(__file__).resolve().parent / "settings.json"
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
    except Exception as e:  # noqa: F841
        # print(f"Error saving settings: {e}")
        pass


# Helper to convert normalized (0.0-1.0) color to byte (0-255) color for Pygame text
def to_byte_color(
    normalized_color: Tuple[float, float, float, float],
) -> Tuple[int, int, int]:
    return tuple(int(c * 255) for c in normalized_color[:3])


settings = load_settings()

# index of resolution
try:
    resolution_index = RESOLUTIONS.index(settings["resolution"])
except:  # noqa: E722
    resolution_index = 0
    settings["resolution"] = RESOLUTIONS[0]


# apply graphics mode
def apply_display_mode(res, fullscreen_flag, vsync_flag):
    global screen, ctx, renderer, fullscreen
    fullscreen = bool(fullscreen_flag)
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    if fullscreen:
        flags |= pygame.FULLSCREEN

    screen = pygame.display.set_mode(res, flags)
    ctx = moderngl.create_context()

    ctx.vsync = bool(vsync_flag)

    ctx.enable(moderngl.BLEND)
    ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
    w, h = res
    renderer = Renderer(ctx, GRID_W, GRID_H, CELL_PADDING, screen_size=res)
    ctx.viewport = (0, 0, w, h)


apply_display_mode(settings["resolution"], settings["fullscreen"], settings["vsync"])

try:
    pygame.mixer.music.load(str(bg_music_path))
    pygame.mixer.music.set_volume(0.5)
    pygame.mixer.music.play(-1)
except Exception as e:
    print("Failed to load BG music:", e)

# -----------------------
# MENU CONFIG
# -----------------------

menu_items = ["Start Game", "Settings", "Fullscreen", "Quit"]
menu_index = 0
menu_anim = 0.0  # breathing animation

settings_items = [
    ("shake_on_death", "Shake on Death"),
    ("resolution", "Resolution"),
    ("fullscreen", "Fullscreen"),
    ("vsync", "V-Sync"),
    ("bloom", "Bloom"),
    ("use_kawase", "Kawase Bloom"),
    ("bloom_strength", "Bloom Strength"),
    ("bloom_radius", "Bloom Radius"),
    ("chroma_enabled", "Chromatic Aberr."),
    ("chroma_amount", "Chroma Amount"),
    ("chroma_bias", "Chroma Falloff"),
    ("color_theme", "Color Theme"),
]
settings_index = 0

# gameover effects
shake_timer = 0.0
shake_duration = 0.6

CHROMA_SPIKE_DURATION = 0.5
MAX_CHROMA_SPIKE = 0.15
chroma_timer = 0.0

# -----------------------
# MAIN LOOP
# -----------------------

preview_acc = 0.0
PREVIEW_TICK = 0.16

while running:
    dt = clock.tick(60) / 1000.0
    if is_transitioning:
        is_transitioning = False
        dt = 0.0

    acc += dt
    menu_anim += dt * 2.5
    preview_acc += dt

    if chroma_timer > 0:
        chroma_timer -= dt

    # input
    for ev in pygame.event.get():
        if ev.type == pygame.QUIT:
            save_settings(settings)
            running = False

        if ev.type == pygame.KEYDOWN:
            # universal escape
            if ev.key == pygame.K_ESCAPE and state != "playing":
                if state == "settings":
                    state = "menu"
                elif state == "gameover":
                    state = "menu"

            # -----------------
            # MAIN MENU INPUT
            # -----------------
            if state == "menu":
                if ev.key == pygame.K_UP:
                    menu_index = (menu_index - 1) % len(menu_items)
                    if snd_select:
                        snd_select.play()
                elif ev.key == pygame.K_DOWN:
                    menu_index = (menu_index + 1) % len(menu_items)
                    if snd_select:
                        snd_select.play()
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    choice = menu_items[menu_index]

                    if choice == "Start Game":
                        snake.reset()
                        state = "playing"
                        acc = 0.0
                        is_transitioning = True
                        if snd_start:
                            snd_start.play()

                    elif choice == "Settings":
                        state = "settings"

                    elif choice == "Fullscreen":
                        settings["fullscreen"] = not settings["fullscreen"]
                        apply_display_mode(
                            settings["resolution"],
                            settings["fullscreen"],
                            settings["vsync"],
                        )
                        save_settings(settings)

                    elif choice == "Quit":
                        running = False

            # -----------------
            # SETTINGS INPUT
            # -----------------
            elif state == "settings":
                if ev.key == pygame.K_UP:
                    settings_index = (settings_index - 1) % len(settings_items)
                    if snd_select:
                        snd_select.play()
                elif ev.key == pygame.K_DOWN:
                    settings_index = (settings_index + 1) % len(settings_items)
                    if snd_select:
                        snd_select.play()
                elif ev.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_RETURN):
                    key, _ = settings_items[settings_index]

                    if key == "color_theme":
                        current_index = THEME_NAMES.index(settings[key])
                        if ev.key == pygame.K_LEFT:
                            new_index = (current_index - 1) % len(THEME_NAMES)
                        else:
                            new_index = (current_index + 1) % len(THEME_NAMES)
                        settings[key] = THEME_NAMES[new_index]
                        save_settings(settings)

                    elif key == "resolution":
                        if ev.key == pygame.K_LEFT:
                            resolution_index = (resolution_index - 1) % len(RESOLUTIONS)
                        else:
                            resolution_index = (resolution_index + 1) % len(RESOLUTIONS)
                        new_res = RESOLUTIONS[resolution_index]
                        settings["resolution"] = new_res
                        apply_display_mode(
                            new_res, settings["fullscreen"], settings["vsync"]
                        )
                        save_settings(settings)

                    elif key in (
                        "bloom_strength",
                        "bloom_radius",
                        "chroma_amount",
                        "chroma_bias",
                    ):
                        step = 0.02
                        if key == "bloom_radius":
                            step = 0.1
                        elif key == "chroma_bias":
                            step = 0.05

                        cur = settings[key]
                        if ev.key == pygame.K_LEFT:
                            settings[key] = max(0.0, cur - step)
                        elif ev.key == pygame.K_RIGHT:
                            settings[key] = min(
                                2.0, cur + step
                            )  # clamp to 2.0 for biases
                        else:
                            settings[key] = DEFAULT_SETTINGS[key]
                        save_settings(settings)

                    else:
                        settings[key] = not settings[key]
                        if key == "vsync" or key == "fullscreen":
                            apply_display_mode(
                                settings["resolution"],
                                settings["fullscreen"],
                                settings["vsync"],
                            )
                        save_settings(settings)

            # -----------------
            # PLAYING INPUT
            # -----------------
            elif state == "playing":
                if ev.key == pygame.K_UP:
                    snake.change_dir((0, -1))
                elif ev.key == pygame.K_DOWN:
                    snake.change_dir((0, 1))
                elif ev.key == pygame.K_LEFT:
                    snake.change_dir((-1, 0))
                elif ev.key == pygame.K_RIGHT:
                    snake.change_dir((1, 0))
                elif ev.key == pygame.K_ESCAPE:
                    state = "menu"

            # -----------------
            # GAME OVER INPUT
            # -----------------
            elif state == "gameover":
                if ev.key == pygame.K_r:
                    snake.reset()
                    acc = 0.0
                    is_transitioning = True
                    state = "playing"
                elif ev.key == pygame.K_m:
                    snake.reset()
                    state = "menu"
            # -----------------
            # WIN INPUT
            # -----------------
            elif state == "win":
                if ev.key == pygame.K_r:
                    snake.reset()
                    state = "playing"
                elif ev.key == pygame.K_m:
                    snake.reset()
                    state = "menu"

    # -----------------------
    # PREVIEW SNAKE LOGIC + AI MOVEMENT TOWARDS APPLE
    # -----------------------
    if state in ("menu", "settings") and preview_acc >= PREVIEW_TICK:
        preview_acc -= PREVIEW_TICK

        head_pos = preview_snake.positions()[0]
        apple_pos = preview_snake.apple

        dx = apple_pos[0] - head_pos[0]
        dy = apple_pos[1] - head_pos[1]

        current_dx, current_dy = preview_snake.direction

        new_dir = (0, 0)

        if abs(dx) > abs(dy):
            new_dir = (1 if dx > 0 else -1, 0)
        elif abs(dy) > 0:
            new_dir = (0, 1 if dy > 0 else -1)

        if new_dir[0] == -current_dx and new_dir[1] == -current_dy:
            if abs(dx) > abs(dy):
                new_dir = (0, 1 if dy > 0 else -1)
            else:
                new_dir = (1 if dx > 0 else -1, 0)

        if new_dir != (0, 0):
            preview_snake.change_dir(new_dir)

        if random.random() < 0.08:
            if random.random() < 0.5:
                # Horizontal turn
                preview_snake.change_dir((random.choice([-1, 1]), 0))
            else:
                # Vertical turn
                preview_snake.change_dir((0, random.choice([-1, 1])))

        ate, died, won = preview_snake.step()

        # Reset the snake if it dies or wins
        if died or won:
            preview_snake.reset()

    # -----------------------
    # GAME LOGIC STEP
    # -----------------------
    if state == "playing" and acc >= TICK:
        acc -= TICK
        ate, died, won = snake.step()
        if ate and snd_apple:
            snd_apple.play()
        if died:
            state = "gameover"
            if snd_gameover:
                snd_gameover.play()
            shake_timer = shake_duration if settings["shake_on_death"] else 0.0
            chroma_timer = CHROMA_SPIKE_DURATION
            final_score = max(0, len(snake.positions()) - 1)
            if final_score > settings["high_score"]:
                settings["high_score"] = final_score
                save_settings(settings)
        elif won:
            state = "win"
            if snd_win:
                snd_win.play()

    # -----------------------
    # RENDERING
    # -----------------------
    renderer.start_frame()

    # Get current theme colors
    current_theme = THEME_COLORS[settings["color_theme"]]
    snake_col = current_theme["snake"]
    apple_col = current_theme["apple"]
    border_col = current_theme["border"]
    title_col = current_theme["title"]

    screen_w = settings["resolution"][0]
    screen_h = settings["resolution"][1]

    # --- PREVIEW RENDER (Runs only in menu/settings) ---
    if state in ("menu", "settings"):
        renderer.draw_border(2, color=(0.08, 0.08, 0.08, 1.0))
        renderer.draw_border(1, color=border_col)
        renderer.draw_snake(preview_snake.positions(), color=snake_col, shake=0.0)
        renderer.draw_apple(preview_snake.apple, color=apple_col, shake=0.0)
        renderer.draw_vignette()

    # -----------------------
    # MENU RENDER
    # -----------------------
    if state == "menu":
        title = "Snake Shader"
        tw = renderer.text_width(title, 82)

        vertical_offset = (screen_h - 800) // 2
        renderer.draw_text(
            title,
            82,
            color=to_byte_color(title_col),
            pos=((screen_w - tw) // 2, vertical_offset),
        )

        high_score_text = f"HIGH SCORE: {settings['high_score']}"
        hs_size = 36
        hs_tw = renderer.text_width(high_score_text, hs_size)

        renderer.draw_text(
            high_score_text,
            hs_size,
            color=(180, 180, 180),
            pos=((screen_w - hs_tw) // 2, vertical_offset + 100),
        )

        menu_text_col = current_theme["menu_text"]
        menu_text_selected_col = current_theme["menu_text_selected"]
        menu_highlight_rect_col = current_theme["menu_highlight_rect"]

        base_y = 340
        for i, item in enumerate(menu_items):
            selected = i == menu_index
            size = 24
            text_w = renderer.text_width(item, size)

            # breathing effect for selected
            scale_add = 0
            if selected:
                scale_add = (0.5 + 0.5 * math.sin(menu_anim)) * 4

                # highlight bar (color is constant)
                renderer.draw_rect(
                    ((screen_w - text_w) // 2 - 22, base_y + i * 60 - 6),
                    (text_w + 50, 44),
                    color=menu_highlight_rect_col,
                    radius=12,
                )

            renderer.draw_text(
                item,
                size + scale_add,
                color=to_byte_color(menu_text_selected_col)
                if selected
                else to_byte_color(menu_text_col),
                pos=((screen_w - text_w) // 2, base_y + i * 60),
            )

    # -----------------------
    # SETTINGS MENU RENDER
    # -----------------------
    elif state == "settings":
        title = "Settings"
        tw = renderer.text_width(title, 72)
        vertical_offset = (screen_h - 800) // 2
        renderer.draw_text(title, 72, pos=((screen_w - tw) // 2, vertical_offset))

        menu_text_col = current_theme["menu_text"]
        menu_text_selected_col = current_theme["menu_text_selected"]
        menu_highlight_rect_col = current_theme["menu_highlight_rect"]

        base_y = 260
        for idx, (key, label) in enumerate(settings_items):
            selected = idx == settings_index
            size = 20

            if key == "color_theme":
                val = settings[key]
            else:
                val = settings[key]
                if isinstance(val, float):
                    # Round float values to 2 decimal places for display
                    val = round(val, 2)
            line = f"{label}: {val}"
            w = renderer.text_width(line, size)

            if selected:
                renderer.draw_rect(
                    ((screen_w - w) // 2 - 20, base_y + idx * 50 - 8),
                    (w + 40, 40),
                    color=menu_highlight_rect_col,
                    radius=12,
                )

            renderer.draw_text(
                line,
                size,
                color=to_byte_color(menu_text_selected_col)
                if selected
                else to_byte_color(menu_text_col),
                pos=((screen_w - w) // 2, base_y + idx * 50),
            )

    # -----------------------
    # GAMEPLAY RENDER
    # -----------------------
    else:
        renderer.draw_border(2, color=(0.08, 0.08, 0.08, 1.0))
        renderer.draw_border(1, color=border_col)

        shake = 0.0
        if state == "gameover" and shake_timer > 0:
            shake = 0.2 * (shake_timer / shake_duration)
            shake_timer -= dt

        renderer.draw_snake(snake.positions(), color=snake_col, shake=shake)
        renderer.draw_apple(snake.apple, color=apple_col, shake=shake)

        score = max(0, len(snake.positions()) - 1)
        score_text = f"SCORE: {score}"

        text_size = 32
        text_w = renderer.text_width(score_text, text_size)

        screen_w = settings["resolution"][0]
        score_pos_x = screen_w - text_w - 20
        score_pos_y = 20

        renderer.draw_text(
            score_text, text_size, color=(255, 255, 255), pos=(score_pos_x, score_pos_y)
        )

        fps = clock.get_fps()
        fps_text = f"FPS: {int(fps)}"

        fps_text_size = 32
        fps_pos_x = 20
        fps_pos_y = 20

        renderer.draw_text(
            fps_text, fps_text_size, color=(255, 255, 255), pos=(fps_pos_x, fps_pos_y)
        )

        if state == "gameover":
            renderer.draw_tint((1, 0, 0, 0.25))
            renderer.draw_text("GAME OVER", 72, pos=(220, 240))
            renderer.draw_text("R = Retry | M = Menu", 28, pos=(240, 330))
        elif state == "win":
            renderer.draw_tint((0, 0.5, 0, 0.25))
            renderer.draw_text("YOU WIN!", 72, pos=(240, 240), color=(255, 255, 255))
            renderer.draw_text(
                "R = Restart | M = Menu", 28, pos=(240, 330), color=(255, 255, 255)
            )

    # -----------------------
    # BLOOM + PRESENT
    # -----------------------
    renderer.set_dirt("src/assets/dirt.jpg")
    renderer.use_kawase = settings["use_kawase"]
    renderer.exposure = settings["exposure"]

    renderer.chroma_enabled = settings["chroma_enabled"]
    if chroma_timer > 0:
        # Normalized time: 1.0 (start) down to 0.0 (end)
        t = max(0.0, chroma_timer / CHROMA_SPIKE_DURATION)
        default_chroma = settings["chroma_amount"]

        # Interpolate from MAX_SPIKE down to the default setting
        current_chroma = default_chroma + (MAX_CHROMA_SPIKE - default_chroma) * t
        renderer.chroma_amount = current_chroma
    else:
        # Use the static setting when the spike is over
        renderer.chroma_amount = settings["chroma_amount"]

    renderer.chroma_bias = settings["chroma_bias"]

    renderer.bloom_pass()
    renderer.present(
        bloom=settings["bloom"],
        bloom_strength=settings["bloom_strength"],
        bloom_radius=settings["bloom_radius"],
    )

    pygame.display.flip()

pygame.quit()
sys.exit()
