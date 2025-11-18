from collections import OrderedDict
from typing import List, Tuple
import random
import numpy as np
import moderngl
import pygame
from pathlib import Path


class Renderer:
    def __init__(
        self,
        ctx: moderngl.Context,
        grid_w: int,
        grid_h: int,
        padding: float = 0.05,
        screen_size: Tuple[int, int] = (800, 800),
    ):
        self.ctx = ctx
        self.grid_w = grid_w
        self.grid_h = grid_h
        self.padding = padding
        self.screen_size = screen_size

        self.shader_dir = Path(__file__).resolve().parent / "shaders"
        renderer_dir = Path(__file__).resolve().parent
        fonts_dir = renderer_dir / "fonts"
        custom_font_path_obj = fonts_dir / "PixelifySans.ttf"
        self.custom_font_path = custom_font_path_obj

        if not self.custom_font_path.exists():
            print(
                f"Warning: Custom font not found at {self.custom_font_path}. Falling back to default."
            )
            self.custom_font_path = (
                None
            )
        # ---- main instanced program (quad.vert / quad.frag) ----
        vert_src = (self.shader_dir / "quad.vert").read_text()
        frag_src = (self.shader_dir / "quad.frag").read_text()
        self.prog = ctx.program(vertex_shader=vert_src, fragment_shader=frag_src)

        # instanced quad
        quad = np.array(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0],
            ],
            dtype="f4",
        )
        self.vbo = ctx.buffer(quad.tobytes())

        max_segments = grid_w * grid_h
        self.instance_buf = ctx.buffer(reserve=max_segments * 8)

        self.vao = ctx.vertex_array(
            self.prog,
            [
                (self.vbo, "2f", "in_vert"),
                (self.instance_buf, "2f/i", "in_offset"),
            ],
        )

        # set uniforms
        if "u_resolution" in self.prog:
            self.prog["u_resolution"].value = (grid_w, grid_h)
        if "u_padding" in self.prog:
            self.prog["u_padding"].value = padding
        if "u_screen" in self.prog:
            self.prog["u_screen"].value = (self.screen_size[0], self.screen_size[1])

        # ---- fullscreen helper shaders ----
        overlay_vert = (self.shader_dir / "overlay.vert").read_text()
        overlay_frag = (self.shader_dir / "overlay.frag").read_text()
        self.overlay_prog = ctx.program(
            vertex_shader=overlay_vert, fragment_shader=overlay_frag
        )

        passthrough_frag = (self.shader_dir / "passthrough.frag").read_text()
        self.blit_prog = ctx.program(
            vertex_shader=overlay_vert, fragment_shader=passthrough_frag
        )

        # text shader
        text_vert = (self.shader_dir / "text.vert").read_text()
        text_frag = (self.shader_dir / "text.frag").read_text()
        self.text_prog = ctx.program(vertex_shader=text_vert, fragment_shader=text_frag)

        # fullscreen VBO/VAOs
        fullscreen = np.array(
            [
                [-1.0, -1.0],
                [1.0, -1.0],
                [1.0, 1.0],
                [-1.0, -1.0],
                [1.0, 1.0],
                [-1.0, 1.0],
            ],
            dtype="f4",
        )
        self.full_vbo = ctx.buffer(fullscreen.tobytes())
        self.full_vao_overlay = ctx.vertex_array(
            self.overlay_prog, [(self.full_vbo, "2f", "in_pos")]
        )
        self.full_vao_blit = ctx.vertex_array(
            self.blit_prog, [(self.full_vbo, "2f", "in_pos")]
        )

        # ---- postprocess: compile Kawase blur & bright-pass & composite inline ----
        # Bright-pass (threshold before blur)
        bright_frag = (self.shader_dir / "brightpass.frag").read_text()
        self.bright_prog = ctx.program(
            vertex_shader=overlay_vert, fragment_shader=bright_frag
        )
        self.full_vao_bright = ctx.vertex_array(
            self.bright_prog, [(self.full_vbo, "2f", "in_pos")]
        )

        # Kawase blur fragment (cheap multi-pass)
        kawase_frag = (self.shader_dir / "kawase.frag").read_text()
        self.kawase_prog = ctx.program(
            vertex_shader=overlay_vert, fragment_shader=kawase_frag
        )
        self.full_vao_kawase = ctx.vertex_array(
            self.kawase_prog, [(self.full_vbo, "2f", "in_pos")]
        )

        # Composite with optional dirt map and ACES-ish tonemap + exposure
        composite_frag = (self.shader_dir / "composite.frag").read_text()
        self.composite_prog = ctx.program(
            vertex_shader=overlay_vert, fragment_shader=composite_frag
        )
        self.full_vao_composite = ctx.vertex_array(
            self.composite_prog, [(self.full_vbo, "2f", "in_pos")]
        )

        # fallback gaussian blur program
        try:
            blur_frag_text = (self.shader_dir / "blur.frag").read_text()
            self.gaussian_prog = ctx.program(
                vertex_shader=overlay_vert, fragment_shader=blur_frag_text
            )
            self.full_vao_gaussian = ctx.vertex_array(
                self.gaussian_prog, [(self.full_vbo, "2f", "in_pos")]
            )
        except Exception:
            self.gaussian_prog = None
            self.full_vao_gaussian = None
        # chromatic aberration program
        chroma_frag = (self.shader_dir / "chroma_aberration.frag").read_text()
        self.chroma_prog = ctx.program(
            vertex_shader=overlay_vert, fragment_shader=chroma_frag
        )
        self.full_vao_chroma = ctx.vertex_array(
            self.chroma_prog, [(self.full_vbo, "2f", "in_pos")]
        )

        # allocate textures/framebuffers
        self._alloc_buffers(self.screen_size[0], self.screen_size[1])

        # bloom parameters
        self.bloom_threshold = 0.85
        self.bloom_gain = 1.4  # per-object multiplier when writing bloom objects
        self.bloom_objects: List[
            Tuple[int, int, Tuple[float, float, float, float]]
        ] = []

        # choose blur algorithm
        self.use_kawase = True

        # dirt map. Loading via set_dirt(path)
        self._dirt_tex_path = None
        self.dirt_tex = None
        self.dirt_strength = 1

        # tonemapping/exposure
        self.exposure = 1.0

        # debug views: None | 'bloom' | 'bright' | 'blur_h' | 'blur_v' | 'blur_final'
        self.debug_mode = None

        # text rendering helpers
        self.text_vbo = ctx.buffer(reserve=6 * (4 * 4))
        self.text_vao = ctx.vertex_array(
            self.text_prog, [(self.text_vbo, "2f 2f", "in_pos", "in_uv")]
        )

        # vertex instance buffer written later
        self.text_cache = OrderedDict()  # replace existing dict
        self.font_cache = {}             # already present
        self.MAX_TEXT_CACHE = 128        # tune this (128 is reasonable)

    # ------------------------------
    # Buffer allocation / resize
    # ------------------------------
    def _alloc_buffers(self, w: int, h: int):
        # release if present
        for attr in [
            "scene_fbo",
            "scene_tex",
            "bloom_fbo",
            "bloom_tex",
            "ping_fbo",
            "ping_tex",
            "pong_fbo",
            "pong_tex",
            "small_ping_fbo",
            "small_ping_tex",
            "small_pong_fbo",
            "small_pong_tex",
        ]:
            if hasattr(self, attr):
                try:
                    getattr(self, attr).release()
                except Exception:
                    pass

        # main scene
        self.scene_tex = self.ctx.texture((w, h), 4)
        self.scene_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.scene_fbo = self.ctx.framebuffer(color_attachments=[self.scene_tex])

        # bloom HDR buffer (float)
        self.bloom_tex = self.ctx.texture((w, h), 4, dtype="f4")
        self.bloom_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.bloom_fbo = self.ctx.framebuffer(color_attachments=[self.bloom_tex])

        # full-res ping/pong (not normally used)
        self.ping_tex = self.ctx.texture((w, h), 4)
        self.pong_tex = self.ctx.texture((w, h), 4)
        self.ping_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.pong_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.ping_fbo = self.ctx.framebuffer(color_attachments=[self.ping_tex])
        self.pong_fbo = self.ctx.framebuffer(color_attachments=[self.pong_tex])

        # half-res ping/pong for blur
        down_w = max(1, w // 2)
        down_h = max(1, h // 2)
        self.small_ping_tex = self.ctx.texture((down_w, down_h), 4)
        self.small_pong_tex = self.ctx.texture((down_w, down_h), 4)
        self.small_ping_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.small_pong_tex.filter = (moderngl.LINEAR, moderngl.LINEAR)
        self.small_ping_fbo = self.ctx.framebuffer(
            color_attachments=[self.small_ping_tex]
        )
        self.small_pong_fbo = self.ctx.framebuffer(
            color_attachments=[self.small_pong_tex]
        )

    def set_screen_size(self, size: Tuple[int, int]):
        self.screen_size = size
        try:
            self.ctx.viewport = (0, 0, size[0], size[1])
        except Exception:
            pass
        self._alloc_buffers(size[0], size[1])

    # ------------------------------
    # Per-frame start
    # ------------------------------
    def start_frame(self):
        # render to scene fbo
        self.scene_fbo.use()
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.ctx.clear(0.05, 0.05, 0.05, 1.0)

        # ensure bloom buffer cleared (HDR float clear)
        self.bloom_fbo.use()
        self.ctx.blend_func = (moderngl.ONE, moderngl.ZERO)
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)

        # restore scene fbo
        self.scene_fbo.use()
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

        # update uniforms if present
        if "u_screen" in self.prog:
            self.prog["u_screen"].value = (self.screen_size[0], self.screen_size[1])
        if "u_resolution" in self.prog:
            self.prog["u_resolution"].value = (self.grid_w, self.grid_h)

    # ------------------------------
    # Bloom pass: render bright objects into bloom_fbo
    # ------------------------------
    def bloom_pass(self):
        """Render collected bloom_objects (positions + color) into bloom_fbo as HDR mask."""
        if not hasattr(self, "bloom_fbo") or not self.bloom_objects:
            # clear list anyway
            self.bloom_objects.clear()
            return

        # ensure bloom fbo cleared and additive blending
        self.bloom_fbo.use()
        self.ctx.blend_func = (moderngl.ONE, moderngl.ZERO)
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.blend_func = (moderngl.ONE, moderngl.ONE)

        # group by color to minimize uniform sets/cache thrash
        by_color = {}
        for x, y, col in self.bloom_objects:
            key = col[:3]
            by_color.setdefault(key, []).append((x, y))

        for col, positions in by_color.items():
            if not positions:
                continue
            self.write_instances(positions)
            if "u_color" in self.prog:
                self.prog["u_color"].value = (col[0], col[1], col[2], 1.0)
            self.vao.render(mode=moderngl.TRIANGLES, instances=len(positions))

        # restore state
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.scene_fbo.use()
        self.bloom_objects.clear()

    # ------------------------------
    # Instance write + draw helpers
    # ------------------------------
    def write_instances(
        self, positions: List[Tuple[int, int]], jitter: Tuple[float, float] = (0.0, 0.0)
    ):
        if jitter != (0.0, 0.0):
            out = []
            for x, y in positions:
                jx = random.uniform(-jitter[0], jitter[0])
                jy = random.uniform(-jitter[1], jitter[1])
                out.append((float(x) + jx, float(y) + jy))
            arr = np.array(out, dtype="f4")
        else:
            arr = np.array(positions, dtype="f4")
        self.instance_buf.write(arr.tobytes())

    def draw_snake(
        self,
        segments: List[Tuple[int, int]],
        color: Tuple[float, float, float, float],
        shake: float = 0.0,
    ):
        if not segments:
            return
        jitter = (shake, shake) if shake else (0.0, 0.0)
        BLOOM_GAIN = self.bloom_gain

        self.write_instances(segments, jitter=jitter)
        if "u_color" in self.prog:
            self.prog["u_color"].value = color
        self.vao.render(mode=moderngl.TRIANGLES, instances=len(segments))

        # Bloom calculation must use the received color
        bloom_col = (
            color[0] * BLOOM_GAIN,
            color[1] * BLOOM_GAIN,
            color[2] * BLOOM_GAIN,
            1.0,
        )
        for x, y in segments:
            self.bloom_objects.append((x, y, bloom_col))

    # Add color argument to draw_apple
    def draw_apple(
        self,
        apple: Tuple[int, int],
        color: Tuple[float, float, float, float],
        shake: float = 0.0,
    ):
        jitter = (shake, shake) if shake else (0.0, 0.0)
        BLOOM_GAIN = self.bloom_gain

        self.write_instances([apple], jitter=jitter)
        if "u_color" in self.prog:
            self.prog["u_color"].value = color
        self.vao.render(mode=moderngl.TRIANGLES, instances=1)

        # Bloom calculation must use the received color
        bloom_col = (
            color[0] * BLOOM_GAIN,
            color[1] * BLOOM_GAIN,
            color[2] * BLOOM_GAIN,
            1.0,
        )
        self.bloom_objects.append((apple[0], apple[1], bloom_col))

    # ------------------------------
    # The combined present() with brightpass + kawase/gaussian + composite
    # ------------------------------
    def present(
        self,
        bloom: bool = False,
        bloom_strength: float = 0.6,
        bloom_radius: float = 2.0,
    ):
        # ----------------------------------------------------
        # DEBUG MODE
        # ----------------------------------------------------
        if self.debug_mode:
            self.ctx.screen.use()
            self.ctx.clear(0.0, 0.0, 0.0, 1.0)
            if self.debug_mode == "bloom":
                self.bloom_tex.use(0)
            elif self.debug_mode == "bright":
                # bright-pass is produced to small_ping during normal present — show what was last computed
                self.small_ping_tex.use(0)
            elif self.debug_mode == "blur_h":
                self.small_pong_tex.use(0)
            elif self.debug_mode == "blur_v":
                self.small_ping_tex.use(0)
            elif self.debug_mode == "blur_final":
                self.small_ping_tex.use(0)
            else:
                self.scene_tex.use(0)
            if "tex" in self.blit_prog:
                self.blit_prog["tex"].value = 0
            self.full_vao_blit.render()
            return

        self.ctx.screen.use()
        self.ctx.clear(0.0, 0.0, 0.0, 1.0)

        # ----------------------------------------------------
        # SIMPLE BLIT (NO BLOOM) + CHROMA CHECK
        # ----------------------------------------------------
        if not bloom:
            # If CA is enabled, render scene through CA, else simple blit
            if self.chroma_enabled and self.chroma_amount > 0.0:
                self.ctx.screen.use()
                self.scene_tex.use(0)
                if "tex" in self.chroma_prog:
                    self.chroma_prog["tex"].value = 0
                if "u_amount" in self.chroma_prog:
                    self.chroma_prog["u_amount"].value = float(self.chroma_amount)
                if "u_center_bias" in self.chroma_prog:
                    self.chroma_prog["u_center_bias"].value = float(self.chroma_bias)
                if "u_resolution" in self.chroma_prog:
                    self.chroma_prog["u_resolution"].value = self.screen_size
                self.full_vao_chroma.render()
            else:
                self.scene_tex.use(0)
                if "tex" in self.blit_prog:
                    self.blit_prog["tex"].value = 0
                self.full_vao_blit.render()
            return

        # prepare downsample sizes
        down_w = max(1, self.screen_size[0] // 2)
        down_h = max(1, self.screen_size[1] // 2)

        # CLEAR small ping/pong to avoid trails
        self.small_ping_fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self.small_pong_fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)

        # 1) BRIGHT-PASS (threshold BEFORE blur) -> small_ping
        self.small_ping_fbo.use()
        # Source is bloom_tex (which bloom_pass wrote HDR bright objects)
        self.bloom_tex.use(0)
        if "tex" in self.bright_prog:
            self.bright_prog["tex"].value = 0
        if "threshold" in self.bright_prog:
            self.bright_prog["threshold"].value = float(self.bloom_threshold)
        self.full_vao_bright.render()

        # 2) BLUR passes (Kawase or Gaussian)
        if self.use_kawase:
            # Kawase multi-pass offsets
            offsets = [1.0, 2.0, 4.0]  # tweak for softness
            src = self.small_ping_tex
            dst_fbo = self.small_pong_fbo
            for off in offsets:
                dst_fbo.use()
                src.use(0)
                if "tex" in self.kawase_prog:
                    self.kawase_prog["tex"].value = 0
                if "offset" in self.kawase_prog:
                    self.kawase_prog["offset"].value = float(off)
                if "texel" in self.kawase_prog:
                    self.kawase_prog["texel"].value = (1.0 / down_w, 1.0 / down_h)
                self.full_vao_kawase.render()

                # swap for next pass
                src = (
                    self.small_pong_tex
                    if dst_fbo is self.small_pong_fbo
                    else self.small_ping_tex
                )
                # alternate dst
                dst_fbo = (
                    self.small_ping_fbo
                    if dst_fbo is self.small_pong_fbo
                    else self.small_pong_fbo
                )
        else:
            # Gaussian separable fallback using gaussian_prog
            if self.gaussian_prog is None:
                # fallback: single blit (no blur)
                self.small_ping_fbo.use()
                self.small_ping_tex.use(0)
                self.full_vao_blit.render()
            else:
                iterations = 3
                base_radius = float(bloom_radius)
                src_ping = self.small_ping_tex
                dst_ping_fbo = self.small_pong_fbo
                for i in range(iterations):
                    # horizontal
                    dst_ping_fbo.use()
                    src_ping.use(0)
                    if "tex" in self.gaussian_prog:
                        self.gaussian_prog["tex"].value = 0
                    if "u_dir" in self.gaussian_prog:
                        self.gaussian_prog["u_dir"].value = (1.0 / down_w, 0.0)
                    if "u_radius" in self.gaussian_prog:
                        self.gaussian_prog["u_radius"].value = base_radius * (
                            1.0 + i * 0.6
                        )
                    self.full_vao_gaussian.render()

                    # vertical
                    src_ping = self.small_pong_tex
                    dst_ping_fbo = self.small_ping_fbo
                    dst_ping_fbo.use()
                    src_ping.use(0)
                    if "tex" in self.gaussian_prog:
                        self.gaussian_prog["tex"].value = 0
                    if "u_dir" in self.gaussian_prog:
                        self.gaussian_prog["u_dir"].value = (0.0, 1.0 / down_h)
                    if "u_radius" in self.gaussian_prog:
                        self.gaussian_prog["u_radius"].value = base_radius * (
                            1.0 + i * 0.6
                        )
                    self.full_vao_gaussian.render()
                    src_ping = self.small_ping_tex
                    dst_ping_fbo = self.small_pong_fbo

        # ----------------------------------------------------
        # 3) COMPOSITE PASS -> PONG FBO (LDR Result)
        # render to pong_fbo instead of the screen to allow for the CA pass.
        # ----------------------------------------------------
        self.pong_fbo.use()
        self.scene_tex.use(0)
        self.small_ping_tex.use(1)

        if "scene" in self.composite_prog:
            self.composite_prog["scene"].value = 0
        if "bloom" in self.composite_prog:
            self.composite_prog["bloom"].value = 1

        # bind dirt map if present
        if self.dirt_tex is not None:
            # ensure dirt is set to texture unit 2
            self.dirt_tex.use(2)
            if "dirt" in self.composite_prog:
                self.composite_prog["dirt"].value = 2
            if "has_dirt" in self.composite_prog:
                self.composite_prog["has_dirt"].value = 1
            if "dirt_strength" in self.composite_prog:
                self.composite_prog["dirt_strength"].value = float(self.dirt_strength)
        else:
            if "has_dirt" in self.composite_prog:
                self.composite_prog["has_dirt"].value = 0

        if "strength" in self.composite_prog:
            self.composite_prog["strength"].value = float(bloom_strength)
        if "exposure" in self.composite_prog:
            self.composite_prog["exposure"].value = float(self.exposure)

        self.full_vao_composite.render()

        # ----------------------------------------------------
        # 4) CHROMA ABERRATION PASS (or FINAL BLIT) -> SCREEN
        # ----------------------------------------------------
        if self.chroma_enabled and self.chroma_amount > 0.0:
            self.ctx.screen.use()
            self.pong_tex.use(0)  # Input is the LDR composite scene

            if "tex" in self.chroma_prog:
                self.chroma_prog["tex"].value = 0
            if "u_amount" in self.chroma_prog:
                self.chroma_prog["u_amount"].value = float(self.chroma_amount)
            if "u_center_bias" in self.chroma_prog:
                self.chroma_prog["u_center_bias"].value = float(self.chroma_bias)
            if "u_resolution" in self.chroma_prog:
                self.chroma_prog["u_resolution"].value = self.screen_size

            self.full_vao_chroma.render()

        else:
            # Final Blit (Composite result to screen, if CA is disabled)
            self.ctx.screen.use()
            self.pong_tex.use(0)
            if "tex" in self.blit_prog:
                self.blit_prog["tex"].value = 0
            self.full_vao_blit.render()

    # ------------------------------
    # Dirt loader
    # ------------------------------
    def set_dirt(self, path):
        # Only load the texture if the path is new or it hasn't been loaded yet
        if path == self._dirt_tex_path:
            return

        try:
            image = pygame.image.load(path).convert_alpha()
            data = pygame.image.tostring(image, "RGBA", True)

            w, h = image.get_size()

            if self.dirt_tex:
                self.dirt_tex.release()

            self.dirt_tex = self.ctx.texture((w, h), 4, data)
            self.dirt_tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            self.dirt_tex.build_mipmaps()

            self._dirt_tex_path = path

        except Exception as e:
            print(f"Failed to load dirt texture from {path}: {e}")
            self.dirt_tex = None
            self._dirt_tex_path = None

    # ------------------------------
    # Tint / text / border
    # ------------------------------
    def draw_tint(self, color=(1.0, 0.0, 0.0, 0.35)):
        if "u_color" in self.overlay_prog:
            self.overlay_prog["u_color"].value = color
        self.full_vao_overlay.render(mode=moderngl.TRIANGLES)

    def _get_font(self, size: int) -> pygame.font.Font:
        """Cache and normalize font sizes to avoid creating tons of font objects."""
        size = int(size)  # normalize: 24 and 24.0 become the same key
        if size in self.font_cache:
            return self.font_cache[size]

        if self.custom_font_path:
            self.font_cache[size] = pygame.font.Font(str(self.custom_font_path), int(size))
        else:
            self.font_cache[size] = pygame.font.SysFont(None, int(size))
        font = self.font_cache[size]
        return font

    def draw_text(self, text: str, size: int, color=(255, 255, 255), pos=(400, 400)):
        """
        Renders text into a moderngl texture and caches it with an LRU policy.
        Avoid caching wildly-changing strings (e.g., FPS displayed as "FPS: 123").
        """
        # normalize inputs
        size = int(size)
        # make color a tuple of ints (immutable)
        color = tuple(int(c) for c in color)

        # cache key
        cache_key = (text, color, size)

        # LRU lookup
        if cache_key in self.text_cache:
            # move to end = mark as recently used
            tex, w, h = self.text_cache.pop(cache_key)
            self.text_cache[cache_key] = (tex, w, h)
        else:
            # create new surface/texture
            font = self._get_font(size)
            surf = font.render(text, True, color)
            w, h = surf.get_width(), surf.get_height()
            data = pygame.image.tostring(surf, "RGBA", True)

            # flip rows for moderngl
            row_stride = w * 4
            flipped = bytearray()
            for row in range(h):
                start = (h - 1 - row) * row_stride
                flipped.extend(data[start : start + row_stride])

            tex = self.ctx.texture((w, h), 4, bytes(flipped))
            tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
            tex.build_mipmaps()

            # insert into LRU cache
            self.text_cache[cache_key] = (tex, w, h)

            # evict oldest if over limit
            if len(self.text_cache) > self.MAX_TEXT_CACHE:
                old_key, (old_tex, _, _) = self.text_cache.popitem(last=False)
                try:
                    old_tex.release()
                except Exception:
                    pass

        # draw
        if "u_screen" in self.text_prog:
            self.text_prog["u_screen"].value = (self.screen_size[0], self.screen_size[1])

        x, y = pos
        quad = np.array(
            [
                [x, y + h, 0.0, 1.0],
                [x + w, y + h, 1.0, 1.0],
                [x + w, y, 1.0, 0.0],
                [x, y + h, 0.0, 1.0],
                [x + w, y, 1.0, 0.0],
                [x, y, 0.0, 0.0],
            ],
            dtype="f4",
        )

        self.text_vbo.write(quad.tobytes())
        tex.use()
        self.text_vao.render(mode=moderngl.TRIANGLES)

    def clear_text_cache(self):
        """Releases and clears all cached text textures."""
        for tex, _, _ in self.text_cache.values():
            try:
                tex.release()
            except Exception:
                pass
        self.text_cache.clear()

    def draw_border(self, thickness: int = 2, color=(0.8, 0.8, 0.8, 1.0)):
        if thickness <= 0:
            return
        w = self.grid_w
        h = self.grid_h
        positions = []
        for x in range(0, w):
            for t in range(thickness):
                positions.append((x, t))
                positions.append((x, h - 1 - t))
        for y in range(thickness, h - thickness):
            for t in range(thickness):
                positions.append((t, y))
                positions.append((w - 1 - t, y))
        self.write_instances(positions)
        if "u_color" in self.prog:
            self.prog["u_color"].value = color
        self.vao.render(mode=moderngl.TRIANGLES, instances=len(positions))

    def draw_vignette(self, intensity=5.0):
        """
        Draws a smooth dark vignette around the screen edges.
        Uses the fullscreen quad with a simple radial falloff.
        """

        # lazy-create the vignette program once
        if not hasattr(self, "_vignette_prog"):
            vignette_frag = (self.shader_dir / "vignette.frag").read_text()
            vignette_vert = (self.shader_dir / "vignette.vert").read_text()
            self._vignette_prog = self.ctx.program(
                vertex_shader=vignette_vert,
                fragment_shader=vignette_frag,
            )

            # full-screen quad (two triangles)
            quad = self.ctx.buffer(data=b"-1 -1  1 -1 -1 1  1 -1  1 1 -1 1")
            self._vignette_vao = self.ctx.vertex_array(
                self._vignette_prog, [(quad, "2f", "in_pos")]
            )

        # set intensity
        self._vignette_prog["intensity"].value = float(intensity)

        # draw full-screen
        self._vignette_vao.render()

    def text_width(self, text: str, size: int):
        font = self._get_font(size)
        surf = font.render(text, True, (255, 255, 255))
        return surf.get_width()

    def text_height(self, text: str, size: int):
        font = self._get_font(size)
        surf = font.render(text, True, (255, 255, 255))
        return surf.get_height()

    def draw_rect(self, pos, size, color=(1.0, 1.0, 1.0, 1.0), radius=0.0):
        """
        Draw a solid rectangle in screen pixel coordinates.
        pos  = (x, y)
        size = (w, h)
        color = RGBA in 0..1
        radius = Corner radius in pixels
        """

        if not hasattr(self, "_rect_prog"):
            rect_vert = (self.shader_dir / "rect.vert").read_text()
            rect_frag = (self.shader_dir / "rect.frag").read_text()
            self._rect_prog = self.ctx.program(
                vertex_shader=rect_vert,
                fragment_shader=rect_frag,
            )

            # VBO holds pos.xy, uv.xy for a quad
            self._rect_vbo = self.ctx.buffer(
                reserve=6 * 16
            )  # 6 vertices * 16 bytes per vertex
            self._rect_vao = self.ctx.vertex_array(
                self._rect_prog, [(self._rect_vbo, "2f 2f", "in_pos", "in_uv")]
            )

        x, y = pos
        w, h = size

        quad = np.array(
            [
                [x, y, 0.0, 1.0],
                [x + w, y, 1.0, 1.0],
                [x + w, y + h, 1.0, 0.0],
                [x, y, 0.0, 1.0],
                [x + w, y + h, 1.0, 0.0],
                [x, y + h, 0.0, 0.0],
            ],
            dtype="f4",
        )

        self._rect_vbo.write(quad.tobytes())

        self._rect_prog["u_screen"].value = (self.screen_size[0], self.screen_size[1])
        self._rect_prog["u_color"].value = color

        self._rect_prog["u_rect_pos"].value = pos
        self._rect_prog["u_rect_size"].value = size
        self._rect_prog["u_radius"].value = radius

        self._rect_vao.render(moderngl.TRIANGLES)
