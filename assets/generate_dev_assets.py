"""
Asset Generator for Developer Window and User Photo Integration.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
USER_PHOTO_PATH = os.path.join(ASSETS_DIR, "developer_photo.png")

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

def create_developer_assets():
    # 1. Developer Left Wallpaper: Tech network with laptop (850x640)
    w_l, h_l = 850, 640
    img_l = Image.new("RGB", (w_l, h_l), color=(8, 30, 75))
    d_l = ImageDraw.Draw(img_l)

    # Blue network gradient
    for y in range(h_l):
        r = int(5 + 10 * (y / h_l))
        g = int(25 + 20 * (y / h_l))
        b = int(65 + 40 * (y / h_l))
        d_l.line([(0, y), (w_l, y)], fill=(r, g, b))

    # Laptop screen graphic
    lx, ly = w_l // 2, h_l // 2 + 40
    d_l.rectangle([lx - 160, ly - 110, lx + 160, ly + 90], fill=(20, 45, 90), outline=(0, 220, 255), width=3)
    d_l.rectangle([lx - 150, ly - 100, lx + 150, ly + 80], fill=(10, 20, 45)) # display
    d_l.rectangle([lx - 140, ly - 90, lx - 20, ly - 10], fill=(0, 180, 240)) # window 1
    d_l.rectangle([lx + 10, ly - 90, lx + 140, ly - 10], fill=(0, 230, 180)) # window 2
    d_l.rectangle([lx - 140, ly + 5, lx + 140, ly + 70], fill=(220, 50, 80)) # window 3
    # Laptop base
    d_l.polygon([(lx - 200, ly + 90), (lx + 200, ly + 90), (lx + 170, ly + 115), (lx - 170, ly + 115)], fill=(30, 55, 100), outline=(0, 220, 255))

    # Glowing Network Nodes
    nodes = [
        (lx - 240, ly - 180), (lx - 100, ly - 200), (lx + 120, ly - 190), (lx + 260, ly - 170),
        (lx - 280, ly - 40), (lx + 280, ly - 20), (lx - 250, ly + 120), (lx + 260, ly + 130),
        (lx - 120, ly + 160), (lx + 130, ly + 160)
    ]
    for i, (x1, y1) in enumerate(nodes):
        for j, (x2, y2) in enumerate(nodes):
            if i < j and math.hypot(x2 - x1, y2 - y1) < 200:
                d_l.line([(x1, y1), (x2, y2)], fill=(0, 160, 230), width=1)
        d_l.ellipse([x1 - 18, y1 - 18, x1 + 18, y1 + 18], outline=(0, 230, 255), width=2)
        d_l.ellipse([x1 - 5, y1 - 5, x1 + 5, y1 + 5], fill=(255, 255, 255))

    img_l.save(os.path.join(ASSETS_DIR, "dev_bg_left.jpg"), quality=95)
    print("Generated dev_bg_left.jpg")

    # 2. Developer Team Bottom Right (490x320)
    w_t, h_t = 490, 320
    img_t = Image.new("RGB", (w_t, h_t), color=(235, 240, 245))
    d_t = ImageDraw.Draw(img_t)

    # Collaborative team around computer monitor
    # Desk
    d_t.rectangle([0, h_t - 70, w_t, h_t], fill=(160, 130, 95))
    # Big iMac monitor
    d_t.rectangle([140, 70, 300, 210], fill=(245, 245, 245), outline=(180, 180, 180), width=2)
    d_t.rectangle([145, 75, 295, 195], fill=(20, 30, 50)) # Screen
    d_t.rectangle([210, 210, 230, 250], fill=(200, 200, 200)) # Stand

    # 4 Software developers (silhouettes in conference)
    devs = [
        (80, 140, (230, 200, 185), (50, 70, 110)),
        (130, 110, (220, 190, 175), (180, 60, 70)),
        (330, 120, (235, 205, 190), (40, 140, 90)),
        (390, 150, (225, 195, 180), (30, 50, 80))
    ]
    for x, y, skin, shirt in devs:
        d_t.ellipse([x - 22, y - 28, x + 22, y + 16], fill=skin)
        d_t.pieslice([x - 35, y + 16, x + 35, y + 90], 180, 360, fill=shirt)

    img_t.save(os.path.join(ASSETS_DIR, "dev_team_bottom.jpg"), quality=95)
    print("Generated dev_team_bottom.jpg")

    # 3. User Portrait Crop for Developer Avatar Badge (180x180)
    if os.path.exists(USER_PHOTO_PATH):
        user_img = Image.open(USER_PHOTO_PATH)
        # Center crop face
        uw, uh = user_img.size
        # The user's face is centered in the 1024x512 image
        fcx, fcy = int(uw * 0.58), int(uh * 0.52)
        crop_radius = int(uh * 0.44)
        avatar = user_img.crop((fcx - crop_radius, fcy - crop_radius, fcx + crop_radius, fcy + crop_radius))
        avatar = avatar.resize((170, 170), Image.Resampling.LANCZOS)
        avatar.convert("RGB").save(os.path.join(ASSETS_DIR, "dev_avatar.jpg"), quality=95)
        print("Generated dev_avatar.jpg with user's photo!")

        # Also update face_recog_left.jpg with the user's high-tech photo!
        user_recog = user_img.resize((660, 620), Image.Resampling.LANCZOS)
        user_recog.convert("RGB").save(os.path.join(ASSETS_DIR, "face_recog_left.jpg"), quality=95)
        print("Updated face_recog_left.jpg with user's photo!")

        # Also update tile_face.png with user's photo!
        tile_w, tile_h = 240, 190
        banner_h = 32
        tile_img = Image.new("RGB", (tile_w, tile_h), color=(0, 0, 0))
        
        face_preview = user_img.resize((tile_w, tile_h - banner_h), Image.Resampling.LANCZOS)
        tile_img.paste(face_preview.convert("RGB"), (0, 0))
        
        # Bottom label strip
        d_tile = ImageDraw.Draw(tile_img)
        d_tile.rectangle([0, tile_h - banner_h, tile_w, tile_h], fill=(0, 10, 90))
        d_tile.line([(0, tile_h - banner_h), (tile_w, tile_h - banner_h)], fill=(0, 120, 220), width=2)
        lbl_font = get_font(11, True)
        bbox = d_tile.textbbox((0, 0), "FACE RECOGNITION", font=lbl_font)
        tw = bbox[2] - bbox[0]
        d_tile.text(((tile_w - tw) // 2, tile_h - banner_h + 7), "FACE RECOGNITION", fill=(255, 255, 255), font=lbl_font)
        tile_img.save(os.path.join(ASSETS_DIR, "tile_face.png"), quality=95)
        print("Updated tile_face.png with user's photo!")

if __name__ == "__main__":
    create_developer_assets()
