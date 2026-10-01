"""
Asset Generator for Help Desk window matching exact screenshot.
"""

import os
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

def create_help_desk_asset():
    w, h = 1366, 660
    img = Image.new("RGB", (w, h), color=(45, 35, 30))
    d = ImageDraw.Draw(img)

    # Rustic Wooden Desk Planks
    plank_h = 45
    for y in range(0, h, plank_h):
        # Wood grain tones
        tone = 40 + (y // plank_h) % 3 * 6
        d.rectangle([0, y, w, y + plank_h], fill=(tone + 10, tone + 2, tone - 5))
        d.line([(0, y + plank_h - 1), (w, y + plank_h - 1)], fill=(20, 15, 10), width=2)
        # Subtle grain streaks
        for x in range(0, w, 60):
            d.line([(x, y + 10), (x + 40, y + 10)], fill=(tone + 18, tone + 8, tone + 2), width=1)

    # Iced Coffee Cup on Top Left
    cx_coffee, cy_coffee = 220, 160
    d.ellipse([cx_coffee - 55, cy_coffee - 55, cx_coffee + 55, cy_coffee + 55], fill=(210, 180, 140), outline=(240, 240, 240), width=4)
    d.ellipse([cx_coffee - 45, cy_coffee - 45, cx_coffee + 45, cy_coffee + 45], fill=(160, 110, 60))
    # Straw
    d.line([(cx_coffee - 60, cy_coffee - 60), (cx_coffee - 10, cy_coffee - 10)], fill=(240, 240, 240), width=6)

    # Smartphone on Left
    sx, sy = 280, 420
    d.rounded_rectangle([sx - 45, sy - 85, sx + 45, sy + 85], radius=12, fill=(245, 245, 250), outline=(180, 180, 185), width=2)
    d.rectangle([sx - 38, sy - 65, sx + 38, sy + 65], fill=(15, 20, 30)) # Screen
    d.ellipse([sx - 10, sy + 70, sx + 10, sy + 78], fill=(220, 220, 225)) # Home button

    # Stationery on Right (Set Square Ruler, Pen, Sunglasses)
    rx, ry = 1080, 320
    # Cyan Set Square Ruler
    d.polygon([(rx, ry - 140), (rx, ry + 100), (rx + 120, ry + 100)], fill=(0, 180, 210))
    d.polygon([(rx + 25, ry - 70), (rx + 25, ry + 75), (rx + 90, ry + 75)], fill=(50, 40, 35))
    # Pen
    d.rectangle([rx - 45, ry - 120, rx - 35, ry + 80], fill=(240, 240, 240), outline=(100, 100, 100))
    # Sunglasses
    sg_x, sg_y = 1140, 180
    d.ellipse([sg_x - 45, sg_y - 25, sg_x - 5, sg_y + 25], fill=(30, 20, 15), outline=(180, 60, 30), width=4)
    d.ellipse([sg_x + 5, sg_y - 25, sg_x + 45, sg_y + 25], fill=(30, 20, 15), outline=(180, 60, 30), width=4)
    d.line([(sg_x - 5, sg_y), (sg_x + 5, sg_y)], fill=(180, 60, 30), width=3)

    # Big Open Laptop in Center
    lx, ly = w // 2, 340
    # Laptop top lid / screen
    d.rounded_rectangle([lx - 340, ly - 200, lx + 340, ly + 20], radius=15, fill=(30, 35, 42), outline=(190, 195, 200), width=3)
    d.rectangle([lx - 325, ly - 185, lx + 325, ly + 10], fill=(12, 16, 24)) # Dark display

    # Laptop keyboard base
    d.polygon([
        (lx - 330, ly + 20), (lx + 330, ly + 20),
        (lx + 370, ly + 260), (lx - 370, ly + 260)
    ], fill=(225, 230, 235), outline=(180, 185, 190))
    # Trackpad
    d.rounded_rectangle([lx - 80, ly + 200, lx + 80, ly + 255], radius=6, fill=(215, 220, 225), outline=(180, 185, 190))
    # Keyboard grid
    d.rectangle([lx - 290, ly + 35, lx + 290, ly + 185], fill=(40, 45, 52), outline=(160, 165, 170))

    # Hands typing on keyboard
    # Left Hand & Arm
    d.polygon([(lx - 280, h), (lx - 190, h), (lx - 120, ly + 140), (lx - 180, ly + 110)], fill=(20, 20, 25)) # Sleeve
    d.ellipse([lx - 160, ly + 100, lx - 70, ly + 160], fill=(235, 205, 190)) # Hand
    # Right Hand & Arm
    d.polygon([(lx + 280, h), (lx + 190, h), (lx + 120, ly + 140), (lx + 180, ly + 110)], fill=(20, 20, 25)) # Sleeve
    d.ellipse([lx + 70, ly + 100, lx + 160, ly + 160], fill=(235, 205, 190)) # Hand

    img.save(os.path.join(ASSETS_DIR, "help_desk_bg.jpg"), quality=95)
    print("Generated help_desk_bg.jpg")

if __name__ == "__main__":
    create_help_desk_asset()
