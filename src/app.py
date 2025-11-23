import sys
import math
import json
import random
import pygame
import moderngl
from pathlib import Path

from .config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, GRID_W, GRID_H, CELL_PADDING, TICK, PREVIEW_TICK,
    THEME_COLORS, THEME_NAMES, RESOLUTIONS, DEFAULT_SETTINGS,
    load_settings, save_settings, to_byte_color
)
from .game import Snake
from .renderer import Renderer
from .input_handler import InputHandler
from .audio_manager import AudioManager

class SnakeGameApp:
    def __init__(self):
        # Pre-initialize mixer to avoid delay/missing audio
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
        except Exception:
            pass
        pygame.init()
        
        self.settings = load_settings()
        self.clock = pygame.time.Clock()
        self.running = True
        self.is_transitioning = False
        self.acc = 0.0
        self.preview_acc = 0.0
        
        # Game State
        self.debug_mode = False
        
        # Effects
        self.menu_anim = 0.0
        self.shake_timer = 0.0
        self.shake_duration = 0.6
        self.chroma_timer = 0.0
        self.CHROMA_SPIKE_DURATION = 0.5
        self.MAX_CHROMA_SPIKE = 0.15
        
        # Game Objects
        self.snake = Snake(GRID_W, GRID_H)
        self.preview_snake = Snake(GRID_W, GRID_H)
        
        self.save_file = Path(__file__).resolve().parent.parent / "savegame.json"
        self.has_save = self.save_file.exists()

        # State
        self.state = "menu"  # menu, settings, playing, gameover, win, paused
        self.menu_items = ["Start Game", "Settings", "Fullscreen", "Quit"]
        if self.has_save:
            self.menu_items.insert(0, "Continue")
            
        self.menu_index = 0
        
        self.pause_items = ["Resume", "Save & Quit", "Quit"]
        self.pause_index = 0
        
        self.settings_items = [
            ("shake_on_death", "Shake on Death"),
            ("resolution", "Resolution"),
            ("fullscreen", "Fullscreen"),
            ("music_volume", "Music Volume"),
            ("sfx_volume", "SFX Volume"),
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
        self.settings_index = 0
        
        # Subsystems
        self.input_handler = InputHandler()
        self.audio_manager = AudioManager()
        
        # Resolution index
        try:
            self.resolution_index = RESOLUTIONS.index(self.settings["resolution"])
        except:
            self.resolution_index = 0
            self.settings["resolution"] = RESOLUTIONS[0]

        # Initialize Display & Renderer
        self.init_display()
        self.apply_settings_to_renderer()
        
        # Game Objects
        self.snake = Snake(GRID_W, GRID_H)
        self.preview_snake = Snake(GRID_W, GRID_H)
        
        # Start Music
        self.audio_manager.set_music_volume(self.settings["music_volume"])
        self.audio_manager.set_sfx_volume(self.settings["sfx_volume"])
        self.audio_manager.play_music()

    def save_game(self):
        data = {
            "snake": self.snake.to_dict(),
            "score": len(self.snake.segments) - 1,
        }
        try:
            with open(self.save_file, "w") as f:
                json.dump(data, f)
            self.has_save = True
            if "Continue" not in self.menu_items:
                self.menu_items.insert(0, "Continue")
        except Exception as e:
            print(f"Error saving game: {e}")

    def load_game(self):
        try:
            with open(self.save_file, "r") as f:
                data = json.load(f)
            self.snake.from_dict(data["snake"])
            return True
        except Exception as e:
            print(f"Error loading game: {e}")
            return False

    def init_display(self):
        flags = pygame.OPENGL | pygame.DOUBLEBUF
        if self.settings["fullscreen"]:
            flags |= pygame.FULLSCREEN
            
        self.screen = pygame.display.set_mode(self.settings["resolution"], flags)
        pygame.display.set_caption("Snake Shader v1.1.1")
        
        self.ctx = moderngl.create_context()
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ctx.vsync = self.settings["vsync"]
        
        w, h = self.settings["resolution"]
        self.ctx.viewport = (0, 0, w, h)
        
        self.renderer = Renderer(
            self.ctx, GRID_W, GRID_H, CELL_PADDING, screen_size=self.settings["resolution"]
        )

    def apply_display_mode(self):
        # Re-initialize display with new settings
        self.init_display()

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            if self.is_transitioning:
                self.is_transitioning = False
                dt = 0.0

            self.acc += dt
            self.menu_anim += dt * 2.5
            
            if self.state in ("menu", "settings"):
                self.preview_acc += dt

            if self.chroma_timer > 0:
                self.chroma_timer -= dt

            self.handle_input()
            self.update()
            self.render()

        pygame.quit()
        sys.exit()

    def apply_settings_to_renderer(self):
        """Pushes current settings values to the renderer."""
        self.renderer.bloom_enabled = self.settings["bloom"]
        self.renderer.use_kawase = self.settings["use_kawase"]
        self.renderer.bloom_strength = self.settings["bloom_strength"]
        self.renderer.bloom_radius = self.settings["bloom_radius"]
        self.renderer.chroma_enabled = self.settings["chroma_enabled"]
        self.renderer.chroma_amount = self.settings["chroma_amount"]
        self.renderer.chroma_bias = self.settings["chroma_bias"]

    def handle_input(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                save_settings(self.settings)
                self.running = False
                return

            action, source = self.input_handler.process_event(ev)
            
            if action == "TOGGLE_DEBUG":
                self.debug_mode = not self.debug_mode
                continue

            if action:
                self.process_action(action)

    def process_action(self, action):
        # Universal Pause/Back
        if action == "PAUSE" and self.state != "playing":
            if self.state == "settings":
                self.state = "menu"
            elif self.state == "gameover":
                self.state = "menu"
            elif self.state == "win":
                self.state = "menu"

        if self.state == "menu":
            self.handle_menu_input(action)
        elif self.state == "settings":
            self.handle_settings_input(action)
        elif self.state == "playing":
            self.handle_playing_input(action)
        elif self.state == "gameover":
            self.handle_gameover_input(action)
        elif self.state == "win":
            self.handle_win_input(action)
        elif self.state == "paused":
            self.handle_paused_input(action)

    def handle_menu_input(self, action):
        if action == "UP":
            self.menu_index = (self.menu_index - 1) % len(self.menu_items)
            self.audio_manager.play_sound("select")
        elif action == "DOWN":
            self.menu_index = (self.menu_index + 1) % len(self.menu_items)
            self.audio_manager.play_sound("select")
        elif action == "ENTER":
            choice = self.menu_items[self.menu_index]
            if choice == "Continue":
                # Assuming self.load_game() is a method that loads the game state
                # and returns True on success, False otherwise.
                # This method is not defined in the provided context,
                # so it would need to be implemented elsewhere.
                if self.load_game():
                    self.state = "playing"
                    self.acc = 0.0
                    self.is_transitioning = True
                    self.audio_manager.play_sound("start")
            elif choice == "Start Game":
                self.snake.reset()
                self.state = "playing"
                self.acc = 0.0
                self.is_transitioning = True
                self.audio_manager.play_sound("start")
            elif choice == "Settings":
                self.state = "settings"
            elif choice == "Fullscreen":
                self.settings["fullscreen"] = not self.settings["fullscreen"]
                self.apply_display_mode()
                save_settings(self.settings)
            elif choice == "Quit":
                self.running = False

    def handle_settings_input(self, action):
        if action == "UP":
            self.settings_index = (self.settings_index - 1) % len(self.settings_items)
            self.audio_manager.play_sound("select")
        elif action == "DOWN":
            self.settings_index = (self.settings_index + 1) % len(self.settings_items)
            self.audio_manager.play_sound("select")
        elif action in ("LEFT", "RIGHT", "ENTER"):
            key, _ = self.settings_items[self.settings_index]
            
            # Toggles
            if key in ("vsync", "bloom", "use_kawase", "shake_on_death", "fullscreen", "chroma_enabled") and action == "ENTER":
                self.settings[key] = not self.settings[key]
                if key in ("vsync", "fullscreen"):
                    self.apply_display_mode()
                save_settings(self.settings)
            
            # Theme Cycler
            elif key == "color_theme":
                current_index = THEME_NAMES.index(self.settings[key])
                if action == "LEFT":
                    new_index = (current_index - 1) % len(THEME_NAMES)
                else:
                    new_index = (current_index + 1) % len(THEME_NAMES)
                self.settings[key] = THEME_NAMES[new_index]
                save_settings(self.settings)
                
            # Resolution Cycler
            elif key == "resolution":
                if action == "LEFT":
                    self.resolution_index = (self.resolution_index - 1) % len(RESOLUTIONS)
                else:
                    self.resolution_index = (self.resolution_index + 1) % len(RESOLUTIONS)
                new_res = RESOLUTIONS[self.resolution_index]
                self.settings["resolution"] = new_res
                self.apply_display_mode()
                save_settings(self.settings)
                
            # Sliders
            elif key in (
                "bloom_strength",
                "bloom_radius",
                "chroma_amount",
                "chroma_bias",
                "music_volume",
                "sfx_volume",
            ):
                step = 0.02
                if key == "bloom_radius":
                    step = 0.1
                elif key == "chroma_bias":
                    step = 0.05
                elif key in ("music_volume", "sfx_volume"):
                    step = 0.05
                
                cur = self.settings[key]
                if action == "LEFT":
                    self.settings[key] = max(0.0, cur - step)
                elif action == "RIGHT":
                    self.settings[key] = min(1.0 if key in ("music_volume", "sfx_volume") else 2.0, cur + step)
                elif action == "ENTER":
                    self.settings[key] = DEFAULT_SETTINGS[key]
                
                # Apply immediate effects
                if key == "music_volume":
                    self.audio_manager.set_music_volume(self.settings[key])
                elif key == "sfx_volume":
                    self.audio_manager.set_sfx_volume(self.settings[key])
                    
                save_settings(self.settings)

    def handle_playing_input(self, action):
        if action == "UP": self.snake.change_dir((0, -1))
        elif action == "DOWN": self.snake.change_dir((0, 1))
        elif action == "LEFT": self.snake.change_dir((-1, 0))
        elif action == "RIGHT": self.snake.change_dir((1, 0))
        elif action == "RIGHT": self.snake.change_dir((1, 0))
        elif action == "PAUSE":
            self.state = "paused"
            self.pause_index = 0

    def handle_gameover_input(self, action):
        if action == "RETRY" or action == "ENTER":
            self.snake.reset()
            self.acc = 0.0
            self.is_transitioning = True
            self.state = "playing"
        elif action == "MENU_QUIT" or action == "PAUSE":
            self.snake.reset()
            self.state = "menu"

    def handle_win_input(self, action):
        if action == "RETRY" or action == "ENTER":
            self.snake.reset()
            self.state = "playing"
        elif action == "MENU_QUIT" or action == "PAUSE":
            self.snake.reset()
            self.state = "menu"

    def handle_paused_input(self, action):
        if action == "UP":
            self.pause_index = (self.pause_index - 1) % len(self.pause_items)
            self.audio_manager.play_sound("select")
        elif action == "DOWN":
            self.pause_index = (self.pause_index + 1) % len(self.pause_items)
            self.audio_manager.play_sound("select")
        elif action == "ENTER":
            choice = self.pause_items[self.pause_index]
            if choice == "Resume":
                self.state = "playing"
            elif choice == "Save & Quit":
                self.save_game()
                self.snake.reset()
                self.state = "menu"
            elif choice == "Quit":
                self.snake.reset()
                self.state = "menu"
        elif action == "PAUSE":
            self.state = "playing"

    def update(self):
        # Preview Snake Logic
        if self.state in ("menu", "settings") and self.preview_acc >= PREVIEW_TICK:
            self.preview_acc -= PREVIEW_TICK
            self.update_preview_snake()

        # Game Logic
        if self.state == "playing" and self.acc >= TICK:
            self.acc -= TICK
            ate, died, won = self.snake.step()
            if ate:
                self.audio_manager.play_sound("apple")
            if died:
                self.state = "gameover"
                self.audio_manager.play_sound("gameover")
                self.shake_timer = self.shake_duration if self.settings["shake_on_death"] else 0.0
                self.chroma_timer = self.CHROMA_SPIKE_DURATION
                final_score = max(0, len(self.snake.positions()) - 1)
                if final_score > self.settings["high_score"]:
                    self.settings["high_score"] = final_score
                    save_settings(self.settings)
            elif won:
                self.state = "win"
                self.audio_manager.play_sound("win")

    def update_preview_snake(self):
        head_pos = self.preview_snake.positions()[0]
        apple_pos = self.preview_snake.apple
        dx = apple_pos[0] - head_pos[0]
        dy = apple_pos[1] - head_pos[1]
        current_dx, current_dy = self.preview_snake.direction
        
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
            self.preview_snake.change_dir(new_dir)
            
        if random.random() < 0.08:
            if random.random() < 0.5:
                self.preview_snake.change_dir((random.choice([-1, 1]), 0))
            else:
                self.preview_snake.change_dir((0, random.choice([-1, 1])))
                
        ate, died, won = self.preview_snake.step()
        if died or won:
            self.preview_snake.reset()

    def render(self):
        self.renderer.start_frame()
        
        current_theme = THEME_COLORS[self.settings["color_theme"]]
        snake_col = current_theme["snake"]
        apple_col = current_theme["apple"]
        border_col = current_theme["border"]
        title_col = current_theme["title"]
        
        screen_w, screen_h = self.settings["resolution"]
        
        # Preview Render
        if self.state in ("menu", "settings"):
            self.renderer.draw_border(2, color=(0.08, 0.08, 0.08, 1.0))
            self.renderer.draw_border(1, color=border_col)
            self.renderer.draw_snake(self.preview_snake.positions(), color=snake_col, shake=0.0)
            self.renderer.draw_apple(self.preview_snake.apple, color=apple_col, shake=0.0)
            self.renderer.draw_vignette()

        # Menu Render
        if self.state == "menu":
            self.render_menu(screen_w, screen_h, title_col, current_theme)
        elif self.state == "settings":
            self.render_settings(screen_w, screen_h, current_theme)
        elif self.state == "paused":
            self.render_gameplay(snake_col, apple_col, border_col)
            self.render_pause(screen_w, screen_h)
        else:
            self.render_gameplay(snake_col, apple_col, border_col)


        # Debug Overlay
        if self.debug_mode:
            self.render_debug(screen_h)

        # Bloom + Present
        self.renderer.set_dirt("src/assets/dirt.jpg")
        self.renderer.use_kawase = self.settings["use_kawase"]
        self.renderer.exposure = self.settings["exposure"]
        self.renderer.chroma_enabled = self.settings["chroma_enabled"]
        
        if self.chroma_timer > 0:
            t = max(0.0, self.chroma_timer / self.CHROMA_SPIKE_DURATION)
            default_chroma = self.settings["chroma_amount"]
            current_chroma = default_chroma + (self.MAX_CHROMA_SPIKE - default_chroma) * t
            self.renderer.chroma_amount = current_chroma
        else:
            self.renderer.chroma_amount = self.settings["chroma_amount"]
            
        self.renderer.chroma_bias = self.settings["chroma_bias"]
        
        self.renderer.bloom_pass()
        self.renderer.present(
            bloom=self.settings["bloom"],
            bloom_strength=self.settings["bloom_strength"],
            bloom_radius=self.settings["bloom_radius"],
        )
        
        pygame.display.flip()
        
    def render_menu(self, screen_w, screen_h, title_col, current_theme):
        title = "Snake Shader"
        tw = self.renderer.text_width(title, 82)
        vertical_offset = (screen_h - 800) // 2
        self.renderer.draw_text(title, 82, color=to_byte_color(title_col), pos=((screen_w - tw) // 2, vertical_offset))
        
        high_score_text = f"HIGH SCORE: {self.settings['high_score']}"
        hs_size = 36
        hs_tw = self.renderer.text_width(high_score_text, hs_size)
        self.renderer.draw_text(high_score_text, hs_size, color=(180, 180, 180), pos=((screen_w - hs_tw) // 2, vertical_offset + 100))
        
        menu_text_col = current_theme["menu_text"]
        menu_text_selected_col = current_theme["menu_text_selected"]
        menu_highlight_rect_col = current_theme["menu_highlight_rect"]
        
        base_y = 340
        for i, item in enumerate(self.menu_items):
            selected = i == self.menu_index
            size = 24
            text_w = self.renderer.text_width(item, size)
            
            scale_add = 0
            if selected:
                scale_add = (0.5 + 0.5 * math.sin(self.menu_anim)) * 4
                self.renderer.draw_rect(
                    ((screen_w - text_w) // 2 - 22, base_y + i * 60 - 6),
                    (text_w + 50, 44),
                    color=menu_highlight_rect_col,
                    radius=12,
                )
            
            self.renderer.draw_text(
                item,
                size + scale_add,
                color=to_byte_color(menu_text_selected_col) if selected else to_byte_color(menu_text_col),
                pos=((screen_w - text_w) // 2, base_y + i * 60),
            )

    def render_settings(self, screen_w, screen_h, current_theme):
        title = "Settings"
        tw = self.renderer.text_width(title, 72)
        vertical_offset = (screen_h - 800) // 2
        self.renderer.draw_text(title, 72, pos=((screen_w - tw) // 2, vertical_offset))
        
        menu_text_col = current_theme["menu_text"]
        menu_text_selected_col = current_theme["menu_text_selected"]
        menu_highlight_rect_col = current_theme["menu_highlight_rect"]
        
        base_y = 260
        for idx, (key, label) in enumerate(self.settings_items):
            selected = idx == self.settings_index
            size = 20
            
            if key == "color_theme":
                val = self.settings[key]
            elif key in ("music_volume", "sfx_volume"):
                val = f"{int(self.settings[key] * 100)}%"
            else:
                val = self.settings[key]
                if isinstance(val, float):
                    val = round(val, 2)
            line = f"{label}: {val}"
            w = self.renderer.text_width(line, size)
            
            if selected:
                self.renderer.draw_rect(
                    ((screen_w - w) // 2 - 20, base_y + idx * 50 - 8),
                    (w + 40, 40),
                    color=menu_highlight_rect_col,
                    radius=12,
                )
            
            self.renderer.draw_text(
                line,
                size,
                color=to_byte_color(menu_text_selected_col) if selected else to_byte_color(menu_text_col),
                pos=((screen_w - w) // 2, base_y + idx * 50),
            )

    def render_pause(self, screen_w, screen_h):
        # Draw a semi-transparent overlay
        self.renderer.draw_rect((0, 0), (screen_w, screen_h), color=(0, 0, 0, 0.5))
        
        title = "PAUSED"
        tw = self.renderer.text_width(title, 72)
        vertical_offset = (screen_h - 400) // 2
        self.renderer.draw_text(title, 72, pos=((screen_w - tw) // 2, vertical_offset))
        
        base_y = vertical_offset + 150
        for i, item in enumerate(self.pause_items):
            selected = i == self.pause_index
            size = 32
            text_w = self.renderer.text_width(item, size)
            
            color = (255, 255, 255) if selected else (150, 150, 150)
            if selected:
                self.renderer.draw_text(f"> {item} <", size, color=color, pos=((screen_w - self.renderer.text_width(f"> {item} <", size)) // 2, base_y + i * 60))
            else:
                self.renderer.draw_text(item, size, color=color, pos=((screen_w - text_w) // 2, base_y + i * 60))

    def render_gameplay(self, snake_col, apple_col, border_col):
        self.renderer.draw_border(2, color=(0.08, 0.08, 0.08, 1.0))
        self.renderer.draw_border(1, color=border_col)
        
        shake = 0.0
        if self.state == "gameover" and self.shake_timer > 0:
            shake = 0.2 * (self.shake_timer / self.shake_duration)
            
        self.renderer.draw_snake(self.snake.positions(), color=snake_col, shake=shake)
        self.renderer.draw_apple(self.snake.apple, color=apple_col, shake=shake)
        
        score = max(0, len(self.snake.positions()) - 1)
        score_text = f"SCORE: {score}"
        text_size = 32
        text_w = self.renderer.text_width(score_text, text_size)
        
        screen_w = self.settings["resolution"][0]
        score_pos_x = screen_w - text_w - 20
        score_pos_y = 20
        
        self.renderer.draw_text(score_text, text_size, color=(255, 255, 255), pos=(score_pos_x, score_pos_y))
        
        fps = self.clock.get_fps()
        fps_text = f"FPS: {int(fps)}"
        self.renderer.draw_text(fps_text, 32, color=(255, 255, 255), pos=(20, 20))
        
        if self.state == "gameover":
            self.renderer.draw_tint((1, 0, 0, 0.25))
            self.renderer.draw_text("GAME OVER", 72, pos=(220, 240))
            self.renderer.draw_text("R = Retry | M = Menu", 28, pos=(240, 330))
        elif self.state == "win":
            self.renderer.draw_tint((0, 0.5, 0, 0.25))
            self.renderer.draw_text("YOU WIN!", 72, pos=(240, 240), color=(255, 255, 255))
            self.renderer.draw_text("R = Restart | M = Menu", 28, pos=(240, 330), color=(255, 255, 255))

    def render_debug(self, screen_h):
        debug_size = 20
        pos_x = 20
        pos_y = screen_h - 40
        
        mode_text = f"MODE: {self.state.upper()}"
        self.renderer.draw_text(mode_text, debug_size, color=(255, 255, 255), pos=(pos_x, pos_y - 50))
        
        source_text = f"SOURCE: {self.input_handler.last_input_source}"
        self.renderer.draw_text(source_text, debug_size, color=(255, 255, 255), pos=(pos_x, pos_y - 25))
        
        debug_text = f"LAST ACTION: {self.input_handler.last_input_action}"
        self.renderer.draw_text(debug_text, debug_size, color=(255, 255, 255), pos=(pos_x, pos_y))

