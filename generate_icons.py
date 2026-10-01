"""
========================================================================================
FaceAttend Ultra-HD Cybernetic Biometric Icon Generator (256x256 Anti-Aliased PNGs)
========================================================================================
Generates crystal-sharp, futuristic vector-like icons for all 8 Dashboard action cards:
1. Student Details (ID & Enrollment)
2. Face Recognition (Biometric Reticle & Scan HUD)
3. Attendance Records (Analytics & Calendar Sync)
4. Help Desk (Support Headset & Contact Directory)
5. Train Data (Neural Synapses & LBPH AI Core)
6. Photos (Dataset Gallery & Camera Aperture)
7. Developer (Engineering Code & System Architecture)
8. Exit System (Cyber Power Switch)
========================================================================================
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)


def draw_hud_brackets(draw, cx, cy, r, color, length=18, width=3):
    """Draws targeting brackets on a circle."""
    # Top-Left
    draw.line([(cx - r, cy - r + length), (cx - r, cy - r), (cx - r + length, cy - r)], fill=color, width=width)
    # Top-Right
    draw.line([(cx + r - length, cy - r), (cx + r, cy - r), (cx + r, cy - r + length)], fill=color, width=width)
    # Bottom-Left
    draw.line([(cx - r, cy + r - length), (cx - r, cy + r), (cx - r + length, cy + r)], fill=color, width=width)
    # Bottom-Right
    draw.line([(cx + r - length, cy + r), (cx + r, cy + r), (cx + r, cy + r - length)], fill=color, width=width)


def make_base_canvas(accent_color, bg_color):
    """Creates a 256x256 anti-aliased base canvas with glowing concentric rings."""
    # We render at 512x512 and downsample to 256x256 with LANCZOS for super-sampled anti-aliasing
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2

    # Background Circle
    draw.ellipse([(32, 32), (size - 32, size - 32)], fill=bg_color, outline=accent_color, width=6)
    draw.ellipse([(52, 52), (size - 52, size - 52)], outline=(56, 189, 248, 80), width=2)
    draw.ellipse([(64, 64), (size - 64, size - 64)], outline=(255, 255, 255, 30), width=2)

    # HUD Brackets
    draw_hud_brackets(draw, cx, cy, 210, accent_color, length=36, width=6)
    return img, draw, cx, cy


def generate_all_icons():
    # -------------------------------------------------------------------------
    # 1. Student Details (tile_student.png) - Cyan/Blue
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((0, 132, 255, 255), (7, 24, 52, 240))
    # Head & Shoulders Silhouette + ID Card Accent
    head_r = 50
    draw.ellipse([(cx - head_r, cy - 85 - head_r), (cx + head_r, cy - 85 + head_r)], fill=(0, 210, 255, 255))
    # Shoulders Arc
    draw.pieslice([(cx - 105, cy - 10), (cx + 105, cy + 170)], 180, 360, fill=(0, 132, 255, 255))
    # ID Card Badge Overlay on chest
    card_w, card_h = 90, 60
    card_x, card_y = cx - card_w//2 + 35, cy + 30
    draw.rectangle([(card_x, card_y), (card_x + card_w, card_y + card_h)], fill=(12, 38, 78, 255), outline=(56, 189, 248, 255), width=3)
    draw.line([(card_x + 10, card_y + 18), (card_x + card_w - 10, card_y + 18)], fill=(0, 210, 255, 255), width=3)
    draw.line([(card_x + 10, card_y + 32), (card_x + card_w - 20, card_y + 32)], fill=(148, 163, 184, 255), width=3)
    draw.line([(card_x + 10, card_y + 44), (card_x + card_w - 35, card_y + 44)], fill=(148, 163, 184, 255), width=3)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_student.png"))

    # -------------------------------------------------------------------------
    # 2. Face Recognition (tile_face.png) - Emerald Green
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((16, 185, 129, 255), (6, 36, 28, 240))
    # Biometric Face Mesh Reticle
    face_w, face_h = 130, 160
    draw.ellipse([(cx - face_w, cy - face_h), (cx + face_w, cy + face_h)], outline=(16, 185, 129, 255), width=5)
    # Eyes Crosshairs
    eye_y = cy - 35
    for ex in [cx - 65, cx + 65]:
        draw.ellipse([(ex - 22, eye_y - 22), (ex + 22, eye_y + 22)], outline=(52, 211, 153, 255), width=4)
        draw.ellipse([(ex - 8, eye_y - 8), (ex + 8, eye_y + 8)], fill=(16, 185, 129, 255))
    # Nose & Mouth Nodes
    draw.line([(cx, cy - 25), (cx - 15, cy + 30), (cx + 15, cy + 30)], fill=(52, 211, 153, 255), width=4)
    draw.arc([(cx - 45, cy + 40), (cx + 45, cy + 90)], 20, 160, fill=(16, 185, 129, 255), width=5)
    # Horizontal Laser Scanner Beam
    draw.line([(cx - 170, cy), (cx + 170, cy)], fill=(52, 211, 153, 255), width=4)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_face.png"))

    # -------------------------------------------------------------------------
    # 3. Attendance Records (tile_attendance.png) - Sky Blue
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((14, 165, 233, 255), (7, 30, 56, 240))
    # Calendar & Analytics Sheet
    sheet_w, sheet_h = 190, 200
    sx, sy = cx - sheet_w//2, cy - sheet_h//2 + 10
    draw.rectangle([(sx, sy), (sx + sheet_w, sy + sheet_h)], fill=(10, 36, 70, 255), outline=(14, 165, 233, 255), width=5)
    # Calendar Header Strip
    draw.rectangle([(sx, sy), (sx + sheet_w, sy + 45)], fill=(14, 165, 233, 255))
    draw.rectangle([(sx + 35, sy - 15), (sx + 55, sy + 10)], fill=(255, 255, 255, 255))
    draw.rectangle([(sx + sheet_w - 55, sy - 15), (sx + sheet_w - 35, sy + 10)], fill=(255, 255, 255, 255))
    # Attendance Checkmarks / Bar Chart Rows
    for r in range(3):
        ry = sy + 65 + r * 40
        draw.line([(sx + 25, ry), (sx + 95, ry)], fill=(148, 163, 184, 255), width=4)
        # Checkmark Icon
        draw.line([(sx + 125, ry), (sx + 138, ry + 12), (sx + 165, ry - 12)], fill=(56, 189, 248, 255), width=5)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_attendance.png"))

    # -------------------------------------------------------------------------
    # 4. Help Desk (tile_help.png) - Amber / Gold
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((245, 158, 11, 255), (38, 26, 8, 240))
    # Support Headset Arc
    headset_r = 105
    draw.arc([(cx - headset_r, cy - headset_r - 20), (cx + headset_r, cy + headset_r - 20)], 180, 360, fill=(245, 158, 11, 255), width=10)
    # Earpads
    draw.rectangle([(cx - headset_r - 18, cy - 35), (cx - headset_r + 14, cy + 45)], fill=(251, 191, 36, 255))
    draw.rectangle([(cx + headset_r - 14, cy - 35), (cx + headset_r + 18, cy + 45)], fill=(251, 191, 36, 255))
    # Microphone Boom
    draw.line([(cx - headset_r, cy + 20), (cx - 40, cy + 85), (cx, cy + 85)], fill=(245, 158, 11, 255), width=6)
    draw.ellipse([(cx, cy + 72), (cx + 26, cy + 98)], fill=(251, 191, 36, 255))
    # Question Mark Emblem inside
    try:
        font = ImageFont.truetype("segoeuib.ttf", 90)
        draw.text((cx, cy - 25), "?", fill=(255, 255, 255, 255), font=font, anchor="mm")
    except Exception:
        draw.text((cx, cy - 25), "?", fill=(255, 255, 255, 255), anchor="mm")
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_help.png"))

    # -------------------------------------------------------------------------
    # 5. Train Data (tile_train.png) - Violet / Purple
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((139, 92, 246, 255), (28, 14, 52, 240))
    # Neural Network / AI Processor Chip
    chip_w = 140
    draw.rectangle([(cx - chip_w//2, cy - chip_w//2), (cx + chip_w//2, cy + chip_w//2)], fill=(45, 20, 85, 255), outline=(139, 92, 246, 255), width=6)
    # Neural Interconnect Nodes
    nodes = [
        (cx - 40, cy - 40), (cx + 40, cy - 40),
        (cx, cy),
        (cx - 40, cy + 40), (cx + 40, cy + 40)
    ]
    # Draw Synapses
    for n1 in nodes:
        for n2 in nodes:
            if n1 != n2:
                draw.line([n1, n2], fill=(167, 139, 250, 180), width=3)
    for nx, ny in nodes:
        draw.ellipse([(nx - 14, ny - 14), (nx + 14, ny + 14)], fill=(196, 181, 253, 255), outline=(139, 92, 246, 255), width=3)
    # Chip Pins Extending Out
    for offset in [-35, 0, 35]:
        draw.line([(cx + offset, cy - chip_w//2), (cx + offset, cy - chip_w//2 - 25)], fill=(139, 92, 246, 255), width=5)
        draw.line([(cx + offset, cy + chip_w//2), (cx + offset, cy + chip_w//2 + 25)], fill=(139, 92, 246, 255), width=5)
        draw.line([(cx - chip_w//2, cy + offset), (cx - chip_w//2 - 25, cy + offset)], fill=(139, 92, 246, 255), width=5)
        draw.line([(cx + chip_w//2, cy + offset), (cx + chip_w//2 + 25, cy + offset)], fill=(139, 92, 246, 255), width=5)
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_train.png"))

    # -------------------------------------------------------------------------
    # 6. Photos (tile_photos.png) - Magenta / Pink
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((236, 72, 153, 255), (42, 12, 32, 240))
    # Dual Photo Frames + Iris Camera Aperture
    frame_w, frame_h = 160, 120
    # Background card tilted/shifted
    draw.rectangle([(cx - frame_w//2 + 20, cy - frame_h//2 - 20), (cx + frame_w//2 + 20, cy + frame_h//2 - 20)], fill=(30, 10, 25, 255), outline=(244, 114, 182, 150), width=4)
    # Foreground card
    draw.rectangle([(cx - frame_w//2 - 15, cy - frame_h//2 + 10), (cx + frame_w//2 - 15, cy + frame_h//2 + 10)], fill=(55, 14, 40, 255), outline=(236, 72, 153, 255), width=5)
    # Sun & Mountain Landscape inside photo
    fx, fy = cx - 15, cy + 10
    draw.ellipse([(fx + 30, fy - 25), (fx + 55, fy)], fill=(251, 113, 133, 255))
    draw.polygon([(fx - 55, fy + 45), (fx - 15, fy - 10), (fx + 25, fy + 45)], fill=(236, 72, 153, 255))
    draw.polygon([(fx + 5, fy + 45), (fx + 35, fy + 10), (fx + 65, fy + 45)], fill=(244, 114, 182, 255))
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_photos.png"))

    # -------------------------------------------------------------------------
    # 7. Developer (tile_developer.png) - Cyan / Teal
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((6, 182, 212, 255), (6, 32, 44, 240))
    # Code Terminal Screen < / >
    term_w, term_h = 180, 140
    tx, ty = cx - term_w//2, cy - term_h//2
    draw.rectangle([(tx, ty), (tx + term_w, ty + term_h)], fill=(8, 24, 38, 255), outline=(6, 182, 212, 255), width=5)
    draw.rectangle([(tx, ty), (tx + term_w, ty + 30)], fill=(6, 182, 212, 255))
    # Window Buttons
    draw.ellipse([(tx + 10, ty + 10), (tx + 20, ty + 20)], fill=(239, 68, 68, 255))
    draw.ellipse([(tx + 26, ty + 10), (tx + 36, ty + 20)], fill=(245, 158, 11, 255))
    draw.ellipse([(tx + 42, ty + 10), (tx + 52, ty + 20)], fill=(16, 185, 129, 255))
    # Code Brackets < / >
    try:
        font = ImageFont.truetype("segoeuib.ttf", 60)
        draw.text((cx, cy + 22), "< / >", fill=(34, 211, 238, 255), font=font, anchor="mm")
    except Exception:
        draw.text((cx, cy + 22), "< / >", fill=(34, 211, 238, 255), anchor="mm")
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_developer.png"))

    # -------------------------------------------------------------------------
    # 8. Exit System (tile_exit.png) - Crimson Red
    # -------------------------------------------------------------------------
    img, draw, cx, cy = make_base_canvas((239, 68, 68, 255), (42, 10, 16, 240))
    # Power Button Standby Symbol
    p_r = 90
    draw.arc([(cx - p_r, cy - p_r + 10), (cx + p_r, cy + p_r + 10)], 300, 240, fill=(239, 68, 68, 255), width=16)
    draw.line([(cx, cy - p_r + 5), (cx, cy + 5)], fill=(248, 113, 113, 255), width=16)
    draw.ellipse([(cx - 8, cy - p_r - 2), (cx + 8, cy - p_r + 14)], fill=(248, 113, 113, 255))
    img = img.resize((256, 256), Image.Resampling.LANCZOS)
    img.save(os.path.join(ASSETS_DIR, "tile_exit.png"))

    print("Successfully generated all 8 Ultra-HD Biometric Icons!")


if __name__ == "__main__":
    generate_all_icons()
