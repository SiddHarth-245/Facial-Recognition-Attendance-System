"""
Asset Generator extension for Training module banners and face mosaic.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))

def get_font(size: int, bold: bool = False):
    font_names = ["segoeui.ttf", "arial.ttf", "calibri.ttf", "tahoma.ttf"]
    if bold:
        font_names = ["segoeuib.ttf", "arialbd.ttf", "calibrib.ttf", "tahomabd.ttf"]
    for name in font_names:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            try:
                win_font = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", name)
                if os.path.exists(win_font):
                    return ImageFont.truetype(win_font, size)
            except Exception:
                pass
    return ImageFont.load_default()

def create_training_assets():
    # 1. Top 3 Face Scanners Banner (1366x260)
    width, height = 1366, 260
    img1 = Image.new("RGB", (width, height), color=(65, 110, 160))
    d1 = ImageDraw.Draw(img1)

    # Blue gradient background
    for y in range(height):
        r = int(60 + 20 * (y / height))
        g = int(105 + 25 * (y / height))
        b = int(155 + 35 * (y / height))
        d1.line([(0, y), (width, y)], fill=(r, g, b))

    # 3 Face Scanner Sections
    seg_w = width // 3
    scan_configs = [
        ((255, 120, 0), "Male 1"),    # Orange bracket
        ((255, 215, 0), "Female"),    # Yellow bracket
        ((0, 220, 255), "Male 2")     # Cyan bracket
    ]

    for i, (bracket_color, label) in enumerate(scan_configs):
        cx = i * seg_w + seg_w // 2
        cy = height // 2

        # Face outline & mesh
        d1.ellipse([cx - 45, cy - 65, cx + 45, cy + 45], fill=(225, 200, 185))
        d1.pieslice([cx - 70, cy + 45, cx + 70, cy + 130], 180, 360, fill=(35, 55, 90))

        # Geometric mesh nodes
        nodes = [
            (cx - 30, cy - 35), (cx + 30, cy - 35), (cx, cy - 40),
            (cx - 18, cy - 15), (cx + 18, cy - 15), (cx, cy),
            (cx - 20, cy + 15), (cx + 20, cy + 15), (cx, cy + 30)
        ]
        for n1 in nodes:
            for n2 in nodes:
                dist = math.hypot(n2[0] - n1[0], n2[1] - n1[1])
                if dist < 45:
                    d1.line([n1, n2], fill=(255, 255, 255), width=1)
        for nx, ny in nodes:
            d1.ellipse([nx - 2, ny - 2, nx + 2, ny + 2], fill=(255, 255, 255))

        # Neon Target Brackets
        bw, bh = 85, 95
        bx1, by1 = cx - bw, cy - bh + 15
        bx2, by2 = cx + bw, cy + bh - 5
        c_len = 24
        # Top-Left
        d1.line([(bx1, by1), (bx1 + c_len, by1)], fill=bracket_color, width=4)
        d1.line([(bx1, by1), (bx1, by1 + c_len)], fill=bracket_color, width=4)
        # Top-Right
        d1.line([(bx2, by1), (bx2 - c_len, by1)], fill=bracket_color, width=4)
        d1.line([(bx2, by1), (bx2, by1 + c_len)], fill=bracket_color, width=4)
        # Bottom-Left
        d1.line([(bx1, by2), (bx1 + c_len, by2)], fill=bracket_color, width=4)
        d1.line([(bx1, by2), (bx1, by2 - c_len)], fill=bracket_color, width=4)
        # Bottom-Right
        d1.line([(bx2, by2), (bx2 - c_len, by2)], fill=bracket_color, width=4)
        d1.line([(bx2, by2), (bx2, by2 - c_len)], fill=bracket_color, width=4)

    img1.save(os.path.join(ASSETS_DIR, "train_top_banner.png"), quality=95)
    print("Generated train_top_banner.png")

    # 2. Bottom Dense Face Mosaic (1366x360)
    img2 = Image.new("RGB", (width, 360), color=(30, 30, 30))
    d2 = ImageDraw.Draw(img2)

    # Generate a grid of varied human faces
    grid_cols, grid_rows = 24, 7
    cell_w, cell_h = width // grid_cols, 360 // grid_rows
    palettes = [
        (235, 205, 190), (220, 185, 160), (200, 160, 135),
        (180, 135, 110), (140, 95, 75), (245, 220, 205)
    ]
    shirt_palettes = [
        (180, 50, 60), (40, 100, 180), (50, 140, 80),
        (220, 160, 40), (90, 60, 120), (50, 60, 70)
    ]

    for r in range(grid_rows):
        for c in range(grid_cols):
            x1, y1 = c * cell_w, r * cell_h
            x2, y2 = (c + 1) * cell_w, (r + 1) * cell_h
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

            # Background cell tint
            bg_tone = (int(35 + (c*7)%30), int(35 + (r*11)%30), int(45 + (c*r*3)%30))
            d2.rectangle([x1, y1, x2, y2], fill=bg_tone, outline=(20, 20, 20), width=1)

            # Face & Body
            skin = palettes[(c * 3 + r * 5) % len(palettes)]
            shirt = shirt_palettes[(c * 7 + r * 2) % len(shirt_palettes)]
            
            # Head
            hr_x, hr_y = min(15, cell_w // 3), min(18, cell_h // 3)
            d2.ellipse([cx - hr_x, cy - hr_y, cx + hr_x, cy + hr_y - 2], fill=skin)
            # Shoulders
            d2.pieslice([cx - cell_w//2 + 4, cy + hr_y - 4, cx + cell_w//2 - 4, y2 + 8], 180, 360, fill=shirt)

    # Add 3 prominent celebrity feature portraits (like Prince Charles, Queen, Bush in the screenshot)
    prominents = [
        (int(width * 0.18), 120, 80, 95, (230, 200, 180), "VIP 1"),
        (int(width * 0.50), 80, 85, 95, (235, 205, 185), "VIP 2"),
        (int(width * 0.50), 250, 85, 95, (225, 195, 175), "VIP 3"),
        (int(width * 0.82), 160, 95, 110, (240, 215, 200), "VIP 4")
    ]
    for px, py, pw, ph, skin, lbl in prominents:
        d2.rectangle([px - pw//2 - 4, py - ph//2 - 4, px + pw//2 + 4, py + ph//2 + 4], fill=(20, 20, 20))
        d2.ellipse([px - pw//3, py - ph//3, px + pw//3, py + ph//3], fill=skin)
        d2.pieslice([px - pw//2, py + ph//5, px + pw//2, py + ph//2 + 15], 180, 360, fill=(30, 45, 75))

    img2.save(os.path.join(ASSETS_DIR, "train_bottom_mosaic.jpg"), quality=95)
    print("Generated train_bottom_mosaic.jpg")

if __name__ == "__main__":
    create_training_assets()
