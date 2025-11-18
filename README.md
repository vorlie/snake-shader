# 🐍 Snake Shader: A Pygame/ModernGL Retrowave Arcade

## ✨ Overview

Snake Shader is a modern take on the classic Snake game, built using **Pygame** for input/window handling and **ModernGL** for GPU-accelerated graphics. It features custom shaders, post-processing effects like Bloom and Chromatic Aberration, and a fully customizable color theme system, transforming the simple arcade experience into a visually dynamic spectacle.

## 🌟 Key Features

- **GPU-Accelerated Rendering:** Uses ModernGL to render all game elements (grid, snake, apple, UI) via custom shaders for high-performance visuals.
- **Custom Post-Processing:** Includes advanced graphical effects such as:
    - **Bloom:** Enhances light sources and adds a vibrant glow.
    - **Kawase Bloom:** An alternative bloom technique for smoother results.
    - **Chromatic Aberration:** Adds a subtle retro distortion effect, spiking on game events.
- **Customizable Theme System:** Easily switch between different color palettes (Classic Green, Cyberpunk, Monochrome) via the Settings menu.
- **Persistent Settings:** Saves high score, themes, and graphics settings (`vsync`, `resolution`, `bloom strength`) to a local `settings.json` file.
- **Fluid Gameplay:** Utilizes a fixed time-step game loop for reliable physics and smooth rendering.
- **Font:** Uses a `PixelifySans` TTF font for a unique UI look and feel.

## 🚀 Getting Started

To run Snake Shader, you need Python and the required libraries (Pygame, ModernGL, etc.). It's strongly recommended to use a virtual environment.

### Prerequisites
- Python 3.13+
- The project dependencies (listed in requirements.txt):
    ```
    pip install pygame moderngl numpy
    ```


### Installation and Setup

1. Clone the repository:
    ```
    git clone [https://github.com/vorlie/snake.git](https://github.com/vorlie/snake.git)
    cd snake-shader
    ```

2. Create and activate a virtual environment:
    ```
    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate

    # Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    ```

3. Install dependencies:
    ```
    pip install -r requirements.txt
    ```
4. Run the game:
    ```
    python main.py
    ```

## 🎮 Controls Table Markdown

| Action | Key(s) | Notes | 
 | ----- | ----- | ----- | 
| **Movement** | `ARROW KEYS` | Standard up, down, left, right movement. | 
| **Menu Select/Action** | `ENTER` / `KP_ENTER` | Confirm menu selection or change settings values. | 
| **Menu Navigation** | `UP` / `DOWN` | Navigate through menu and settings options. | 
| **Settings Adjust** | `LEFT` / `RIGHT` | Change values for theme, resolution, and effect settings. | 
| **Pause/Menu** | `ESC` | Exit game state back to the main menu. | 
| **Retry (Game Over)** | `R` | Quickly restart the game after death. | 

## ⚙️ Configuration & Settings Table Markdown

| Setting | Type | Description | 
 | ----- | ----- | ----- | 
| **Resolution** | Cycle | Currently supported: 1920x1080 | 
| **Fullscreen** | Toggle | Switch between windowed and full-screen modes. | 
| **VSync** | Toggle | Synchronizes frame rate with display refresh rate. | 
| **Shake on Death** | Toggle | Enables screen shake effect when the snake dies. | 
| **Color Theme** | Cycle | Choose from predefined color palettes (e.g., Cyberpunk, Classic). | 
| **Bloom** | Toggle | Enables or disables the core light glowing effect. | 
| **Kawase Bloom** | Toggle | Uses the Kawase blur technique for Bloom (better performance). | 
| **Chroma Aberr.** | Toggle | Enables or disables the chromatic aberration effect. | 
| **Bloom Strength** | Adjustable (Arrows) | Adjusts the overall intensity of the Bloom effect. | 
| **Bloom Radius** | Adjustable (Arrows) | Controls the size/spread of the Bloom effect. | 
| **Chroma Amount** | Adjustable (Arrows) | Adjusts the strength of the chromatic distortion. | 
| **Chroma Falloff** | Adjustable (Arrows) | Controls the bias/direction of the chromatic effect. |