"""
Generate a modern Video Downloader app icon (512x512 PNG).
Uses Pillow to create a vibrant gradient icon with a play-download symbol.
"""

from PIL import Image, ImageDraw, ImageFilter, ImageFont
import math

SIZE = 512
CENTER = SIZE // 2

def lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(len(c1)))

def radial_gradient(size, c_center, c_edge):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    cx, cy = size // 2, size // 2
    max_r = math.sqrt(cx**2 + cy**2)
    for y in range(size):
        for x in range(size):
            r = math.sqrt((x - cx)**2 + (y - cy)**2)
            t = min(r / max_r, 1.0)
            t = t ** 0.7  # bias toward center color
            color = lerp_color(c_center, c_edge, t)
            img.putpixel((x, y), color + (255,))
    return img


def create_icon():
    # Create base image
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # --- Rounded square background with gradient ---
    # Create gradient background
    bg_top = (115, 69, 255)      # #7345FF vivid purple
    bg_bottom = (36, 188, 255)   # #24BCFF cyan

    bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for y in range(SIZE):
        t = y / SIZE
        # Diagonal gradient (top-left purple to bottom-right cyan)
        t2 = t * 0.7 + 0.15
        color = lerp_color(bg_top, bg_bottom, t2)
        for x in range(SIZE):
            tx = x / SIZE
            blend = (t + tx) / 2
            blend = max(0, min(1, blend * 0.8 + 0.1))
            c = lerp_color(bg_top, bg_bottom, blend)
            bg.putpixel((x, y), c + (255,))

    # Create rounded rectangle mask
    corner_radius = 110
    mask = Image.new("L", (SIZE, SIZE), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=corner_radius,
        fill=255
    )

    # Apply mask to gradient
    bg.putalpha(mask)
    img = Image.alpha_composite(img, bg)

    # --- Add subtle inner glow / shine ---
    shine = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shine_draw = ImageDraw.Draw(shine)
    # Top-left highlight ellipse
    for i in range(40):
        alpha = int(12 * (1 - i / 40))
        shine_draw.ellipse(
            [20 + i*2, 20 + i*2, SIZE//2 - i*1, SIZE//2 - i*1],
            fill=(255, 255, 255, alpha)
        )
    shine.putalpha(Image.composite(
        shine.split()[3], Image.new("L", (SIZE, SIZE), 0), mask
    ))
    img = Image.alpha_composite(img, shine)

    # --- Draw the play-download icon ---
    draw = ImageDraw.Draw(img)

    # Play triangle (YouTube style) - shifted up
    play_cx = CENTER
    play_cy = CENTER - 40
    play_size = 100

    # Triangle points (pointing right, like a play button)
    tri_pts = [
        (play_cx - play_size * 0.45, play_cy - play_size * 0.55),
        (play_cx - play_size * 0.45, play_cy + play_size * 0.55),
        (play_cx + play_size * 0.6, play_cy),
    ]

    # White play triangle with slight shadow
    shadow_offset = 4
    shadow_pts = [(p[0] + shadow_offset, p[1] + shadow_offset) for p in tri_pts]
    draw.polygon(shadow_pts, fill=(0, 0, 0, 40))
    draw.polygon(tri_pts, fill=(255, 255, 255, 240))

    # --- Download arrow below play button ---
    arrow_cx = CENTER
    arrow_top = CENTER + 60
    arrow_bottom = CENTER + 140
    arrow_width = 22
    arrow_head_w = 55
    arrow_head_start = CENTER + 95

    # Arrow shaft
    draw.rounded_rectangle(
        [(arrow_cx - arrow_width//2, arrow_top),
         (arrow_cx + arrow_width//2, arrow_bottom - 10)],
        radius=8,
        fill=(255, 255, 255, 230)
    )

    # Arrow head (downward triangle)
    head_pts = [
        (arrow_cx - arrow_head_w, arrow_head_start),
        (arrow_cx + arrow_head_w, arrow_head_start),
        (arrow_cx, arrow_bottom + 20),
    ]
    draw.polygon(head_pts, fill=(255, 255, 255, 230))

    # --- Tray / base line ---
    tray_y = arrow_bottom + 38
    tray_left = CENTER - 80
    tray_right = CENTER + 80
    tray_width = 8

    draw.rounded_rectangle(
        [(tray_left, tray_y), (tray_right, tray_y + tray_width)],
        radius=4,
        fill=(255, 255, 255, 200)
    )

    # Small corner bits on the tray (like a download inbox)
    corner_h = 28
    draw.rounded_rectangle(
        [(tray_left, tray_y - corner_h), (tray_left + tray_width, tray_y + tray_width)],
        radius=3,
        fill=(255, 255, 255, 200)
    )
    draw.rounded_rectangle(
        [(tray_right - tray_width, tray_y - corner_h), (tray_right, tray_y + tray_width)],
        radius=3,
        fill=(255, 255, 255, 200)
    )

    # --- Add subtle outer shadow/glow for depth ---
    # Create a version with border glow
    final = Image.new("RGBA", (SIZE + 20, SIZE + 20), (0, 0, 0, 0))
    # Shadow layer
    shadow = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [(0, 0), (SIZE - 1, SIZE - 1)],
        radius=corner_radius,
        fill=(0, 0, 0, 50)
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    final.paste(shadow, (14, 16), shadow)
    final.paste(img, (10, 10), img)

    # Crop back to 512x512
    final = final.resize((SIZE, SIZE), Image.LANCZOS)

    # Save
    final.save("assets/icon.png", "PNG")
    print(f"Icon saved to assets/icon.png ({SIZE}x{SIZE})")


if __name__ == "__main__":
    create_icon()
