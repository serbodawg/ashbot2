from __future__ import annotations

"""
Generate AshBot 2 logo using pycairo.
"""

import math
import cairo


def generate_logo(path: str = "/home/serbodawg/Obrazy/AshBot2_logo.png", size: int = 512) -> None:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = cairo.Context(surface)

    cx = cy = size // 2

    # Background (transparent)
    ctx.set_source_rgba(0, 0, 0, 0)
    ctx.paint()

    # Outer glow circles
    for r in range(220, 190, -10):
        alpha = 0.12 * (1 - (220 - r) / 30)
        ctx.arc(cx, cy, r, 0, 2 * math.pi)
        ctx.set_source_rgba(79 / 255, 195 / 255, 247 / 255, alpha)
        ctx.fill()

    # Hexagon shield
    def draw_hexagon(r, fill_color):
        ctx.move_to(cx + r * math.cos(math.radians(0 - 30)), cy + r * math.sin(math.radians(0 - 30)))
        for i in range(1, 7):
            angle = math.radians(i * 60 - 30)
            ctx.line_to(cx + r * math.cos(angle), cy + r * math.sin(angle))
        ctx.close_path()
        ctx.set_source_rgba(*fill_color)
        ctx.fill()

    draw_hexagon(180, (10 / 255, 22 / 255, 50 / 255, 0.95))
    draw_hexagon(160, (20 / 255, 40 / 255, 80 / 255, 0.8))

    # Hexagon border
    ctx.move_to(cx + 180 * math.cos(math.radians(0 - 30)), cy + 180 * math.sin(math.radians(0 - 30)))
    for i in range(1, 7):
        angle = math.radians(i * 60 - 30)
        ctx.line_to(cx + 180 * math.cos(angle), cy + 180 * math.sin(angle))
    ctx.close_path()
    ctx.set_source_rgba(79 / 255, 195 / 255, 247 / 255, 0.8)
    ctx.set_line_width(4)
    ctx.stroke()

    # Inner hex border
    ctx.move_to(cx + 176 * math.cos(math.radians(0 - 30)), cy + 176 * math.sin(math.radians(0 - 30)))
    for i in range(1, 7):
        angle = math.radians(i * 60 - 30)
        ctx.line_to(cx + 176 * math.cos(angle), cy + 176 * math.sin(angle))
    ctx.close_path()
    ctx.set_source_rgba(124 / 255, 77 / 255, 255 / 255, 0.6)
    ctx.set_line_width(2)
    ctx.stroke()

    # Corner accent dots
    for angle in range(0, 360, 60):
        rad = math.radians(angle - 30)
        x = cx + 170 * math.cos(rad)
        y = cy + 170 * math.sin(rad)
        ctx.arc(x, y, 5, 0, 2 * math.pi)
        ctx.set_source_rgba(79 / 255, 195 / 255, 247 / 255, 0.9)
        ctx.fill()

    # Letter A
    ctx.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(160)

    # Get text extents
    x_bearing, y_bearing, tw, th, _, _ = ctx.text_extents("A")
    tx = cx - tw / 2 - x_bearing
    ty = cy - th / 2 - y_bearing

    # Shadow
    ctx.move_to(tx + 4, ty + 4)
    ctx.set_source_rgba(0, 0, 0, 0.3)
    ctx.show_text("A")

    # Main A
    ctx.move_to(tx, ty)
    ctx.set_source_rgba(79 / 255, 195 / 255, 247 / 255, 1)
    ctx.show_text("A")

    # Bottom accent bar
    bar_y = cy + 70
    bar_w = 120
    bar_h = 5
    r = 2.5
    x0, y0, x1, y1 = cx - bar_w // 2, bar_y, cx + bar_w // 2, bar_y + bar_h
    ctx.move_to(x0 + r, y0)
    ctx.line_to(x1 - r, y0)
    ctx.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
    ctx.line_to(x1, y1 - r)
    ctx.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
    ctx.line_to(x0 + r, y1)
    ctx.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
    ctx.line_to(x0, y0 + r)
    ctx.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()
    ctx.set_source_rgba(79 / 255, 195 / 255, 247 / 255, 0.7)
    ctx.fill()

    # Orbiting dots
    for angle in range(0, 360, 15):
        rad = math.radians(angle)
        r = 205
        dot_x = cx + r * math.cos(rad)
        dot_y = cy + r * math.sin(rad)
        alpha = 0.3 + 0.4 * abs(math.sin(rad * 3))
        ctx.arc(dot_x, dot_y, 2, 0, 2 * math.pi)
        ctx.set_source_rgba(79 / 255, 195 / 255, 247 / 255, alpha)
        ctx.fill()

    surface.write_to_png(path)
    print(f"Logo saved to {path} ({size}x{size})")


if __name__ == "__main__":
    import os
    os.makedirs("/home/serbodawg/Obrazy", exist_ok=True)
    generate_logo()
