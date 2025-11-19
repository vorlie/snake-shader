# Snake Shader 🐍✨

Welcome to **Snake Shader**, a high-performance, retro-futuristic reimplementation of the classic Snake game. I've ditched the basic 2D grids for a fully GPU-accelerated experience using **ModernGL** and **Pygame**.

Think neon lights, smooth animations, and shader effects that make your eyes happy.

## Why is this cool?

Most Snake games just move a square on a screen. This one uses:
- **Custom Shaders**: Everything you see is rendered via OpenGL shaders.
- **Post-Processing**: I've added Bloom (glow), Chromatic Aberration (retro glitch), and Vignette effects.
- **Dynamic Audio**: Sound effects and background music that fit the vibe.
- **Controller Support**: Play with your keyboard or your favorite gamepad.

## 🛠️ Under the Hood

I recently refactored the codebase to be clean, modular, and easy to extend. Here's how it's organized:

- **`main.py`**: The entry point. Short and sweet.
- **`src/app.py`**: The brain of the operation. Manages the game loop and states.
- **`src/game.py`**: The core logic. Handles the snake's movement, growth, and collision rules.
- **`src/renderer.py`**: The artist. Handles all the OpenGL magic and post-processing.
- **`src/shaders/`**: The secret sauce. GLSL shader files for that visual punch.
- **`src/input_handler.py`**: The translator. Converts keyboard and controller presses into game actions.
- **`src/audio_manager.py`**: The DJ. Handles sound effects and music.
- **`src/config.py`**: The rulebook. Centralized settings and constants.

## 🚀 Getting Started

### Prerequisites
You'll need **Python 3.13+**. I recommend using a virtual environment.

### Installation

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/vorlie/snake-shader.git
    cd snake-shader
    ```

2.  **Set up your environment:**
    ```bash
    # Using uv (recommended)
    uv venv
    source .venv/bin/activate
    uv pip install -r requirements.txt
    
    # Or standard pip
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Run it:**
    ```bash
    python main.py
    # or with uv
    uv run main.py
    ```

## 🎮 Controls

| Action | Keyboard | Controller |
| :--- | :--- | :--- |
| **Move** | Arrow Keys | D-Pad / Left Stick |
| **Select / Confirm** | Enter | A / Cross |
| **Back / Pause** | Esc | B / Circle |
| **Debug Info** | D | - |
| **Reset (Game Over)** | R | A / Cross |

## ⚙️ Customization

Check out the **Settings** menu to tweak the experience:
- **Themes**: Switch between "Classic Green", "Cyberpunk", and "Monochrome".
- **Graphics**: Toggle Bloom, V-Sync, and Fullscreen.
- **Effects**: Adjust Bloom intensity and Chromatic Aberration levels to your liking.

---
Built with ❤️, Python, and a lot of shaders.