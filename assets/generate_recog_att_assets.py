"""
Asset Generator for Face Recognition and Attendance System exact UI graphics.
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

def create_face_recognition_assets():
    # 1. Face Recognition Left Side: Man Portrait with Biometric Eye Scanner (650x600)
    w, h = 650, 600
    img_left = Image.new("RGB", (w, h), color=(10, 20, 40))
    d_l = ImageDraw.Draw(img_left)

    # Dark cyber gradient
    for y in range(h):
        r = int(8 + 15 * (y / h))
        g = int(18 + 25 * (y / h))
        b = int(38 + 45 * (y / h))
        d_l.line([(0, y), (w, y)], fill=(r, g, b))

    # Man face silhouette
    cx, cy = w // 2 - 20, h // 2
    d_l.ellipse([cx - 160, cy - 200, cx + 160, cy + 180], fill=(210, 190, 175))
    d_l.pieslice([cx - 240, cy + 150, cx + 240, cy + 450], 180, 360, fill=(20, 35, 60))

    # Beard
    d_l.arc([cx - 100, cy + 40, cx + 100, cy + 160], 0, 180, fill=(60, 45, 35), width=35)
    # Eyes
    eye_lx, eye_rx, eye_y = cx - 60, cx + 60, cy - 35
    d_l.ellipse([eye_lx - 25, eye_y - 15, eye_lx + 25, eye_y + 15], fill=(255, 255, 255))
    d_l.ellipse([eye_lx - 12, eye_y - 12, eye_lx + 12, eye_y + 12], fill=(40, 90, 140))
    d_l.ellipse([eye_rx - 25, eye_y - 15, eye_rx + 25, eye_y + 15], fill=(255, 255, 255))
    d_l.ellipse([eye_rx - 12, eye_y - 12, eye_rx + 12, eye_y + 12], fill=(40, 90, 140))

    # Glowing Biometric Circular HUD over Left/Right Eye (Matching Screenshot 1)
    hud_x, hud_y = eye_rx + 10, eye_y - 5
    for rad in [45, 65, 80]:
        d_l.ellipse([hud_x - rad, hud_y - rad, hud_x + rad, hud_y + rad], outline=(0, 220, 255), width=2)
    # Triangles and crosshairs
    for ang in [0, 60, 120, 180, 240, 300]:
        rad = math.radians(ang)
        x1 = hud_x + int(65 * math.cos(rad))
        y1 = hud_y + int(65 * math.sin(rad))
        x2 = hud_x + int(85 * math.cos(rad))
        y2 = hud_y + int(85 * math.sin(rad))
        d_l.line([(x1, y1), (x2, y2)], fill=(0, 240, 255), width=3)

    img_left.save(os.path.join(ASSETS_DIR, "face_recog_left.jpg"), quality=95)
    print("Generated face_recog_left.jpg")

    # 2. Face Recognition Right Side: Cyber Mesh with Scan Laser & Button area (680x600)
    w_r, h_r = 680, 600
    img_right = Image.new("RGB", (w_r, h_r), color=(5, 12, 30))
    d_r = ImageDraw.Draw(img_right)

    # Dark blue/purple grid background
    for x in range(0, w_r, 40):
        d_r.line([(x, 0), (x, h_r)], fill=(12, 28, 65), width=1)
    for y in range(0, h_r, 40):
        d_r.line([(0, y), (w_r, y)], fill=(12, 28, 65), width=1)

    # Futuristic Wireframe Head Card Container
    card_x1, card_y1, card_x2, card_y2 = 80, 40, w_r - 80, h_r - 60
    d_r.rounded_rectangle([card_x1, card_y1, card_x2, card_y2], radius=15, outline=(0, 180, 240), width=2)
    
    # Title inside card: FACE RECOGNITION
    d_r.text((card_x1 + 160, card_y1 + 18), "FACE RECOGNITION", fill=(200, 230, 255), font=get_font(14, True))

    # 3D Cyber Face Contour Mesh
    mcx, mcy = (card_x1 + card_x2) // 2, (card_y1 + card_y2) // 2 - 20
    d_r.ellipse([mcx - 90, mcy - 120, mcx + 90, mcy + 90], outline=(0, 220, 255), width=2)
    
    # Grid contour rings
    for r in range(25, 95, 20):
        d_r.ellipse([mcx - r, mcy - int(r * 1.3), mcx + r, mcy + int(r * 1.0)], outline=(0, 180, 230), width=1)
    
    # Glowing Laser Scan Line across middle
    d_r.line([(card_x1 + 10, mcy), (card_x2 - 10, mcy)], fill=(0, 255, 255), width=3)
    d_r.ellipse([mcx - 12, mcy - 12, mcx + 12, mcy + 12], fill=(255, 255, 255))

    # Scanning Progress Bar
    p_x1, p_y1 = card_x1 + 60, card_y2 - 75
    p_x2, p_y2 = card_x2 - 60, card_y2 - 58
    d_r.rectangle([p_x1, p_y1, p_x2, p_y2], outline=(0, 190, 255), width=1)
    # Fill 58%
    fill_w = int((p_x2 - p_x1) * 0.58)
    d_r.rectangle([p_x1 + 2, p_y1 + 2, p_x1 + fill_w, p_y2 - 2], fill=(0, 150, 240))
    d_r.text(((p_x1 + p_x2) // 2 - 45, p_y1 - 18), "scanning 58%", fill=(220, 240, 255), font=get_font(10, True))

    img_right.save(os.path.join(ASSETS_DIR, "face_recog_right.jpg"), quality=95)
    print("Generated face_recog_right.jpg")

def create_attendance_assets():
    # 3. Attendance Header Banner: Classroom Lecture Hall (1366x140)
    w, h = 1366, 140
    img_h = Image.new("RGB", (w, h), color=(255, 255, 255))
    d_h = ImageDraw.Draw(img_h)

    # Top strip (Height: 85): Lecture hall students
    strip_h = 85
    cols = [(75, 95, 125), (55, 85, 115), (85, 65, 100), (65, 95, 105), (95, 80, 65), (50, 80, 115)]
    w_seg = w // 6
    for i in range(6):
        x1 = i * w_seg
        x2 = (i + 1) * w_seg if i < 5 else w
        d_h.rectangle([x1, 0, x2, strip_h], fill=cols[i])
        
        # Classroom students silhouettes
        cx, cy = (x1 + x2) // 2, strip_h // 2 + 5
        d_h.ellipse([cx - 14, cy - 20, cx + 14, cy + 8], fill=(230, 210, 195))
        d_h.pieslice([cx - 22, cy + 8, cx + 22, cy + 35], 180, 360, fill=(200, 220, 240))
        
        # Detection box
        if i in [0, 1, 3, 5]:
            d_h.rectangle([cx - 20, cy - 26, cx + 20, cy + 14], outline=(0, 255, 160) if i % 2 == 0 else (0, 220, 255), width=2)

    # Sub-bar (Height: 55): Green Title Bar
    d_h.rectangle([0, strip_h, w, h], fill=(255, 255, 255))
    d_h.line([(0, strip_h), (w, strip_h)], fill=(21, 128, 61), width=2)

    # Title: STUDENT ATTENDANCE MANAGEMENT SYSTEM (Bold Green)
    title_text = "STUDENT ATTENDANCE MANAGEMENT SYSTEM"
    font_title = get_font(24, bold=True)
    try:
        bbox = d_h.textbbox((0, 0), title_text, font=font_title)
        tw = bbox[2] - bbox[0]
    except Exception:
        tw = 680
    d_h.text(((w - tw) // 2, strip_h + 12), title_text, fill=(21, 128, 61), font=font_title)

    img_h.save(os.path.join(ASSETS_DIR, "attendance_header.png"), quality=95)
    print("Generated attendance_header.png")

    # 4. Attendance Form Banner: 4 Girls with Detection Boxes & Name tags (550x120)
    img_girls = Image.new("RGB", (550, 120), color=(240, 245, 250))
    d_g = ImageDraw.Draw(img_girls)

    tags = [("Carrie", (70, 60)), ("Kate", (190, 60)), ("Nicole", (310, 60)), ("Jessica", (430, 60))]
    for name, (gx, gy) in tags:
        # Girl portrait
        d_g.ellipse([gx - 28, gy - 32, gx + 28, gy + 24], fill=(235, 205, 190))
        d_g.pieslice([gx - 38, gy + 20, gx + 38, gy + 70], 180, 360, fill=(210, 100, 120))
        # Blue/cyan detection box
        d_g.rectangle([gx - 35, gy - 38, gx + 35, gy + 28], outline=(0, 180, 240), width=2)
        # Name tag badge
        d_g.rectangle([gx - 28, gy + 28, gx + 28, gy + 44], fill=(0, 140, 210))
        d_g.text((gx - 18, gy + 30), name, fill=(255, 255, 255), font=get_font(9, True))

    img_girls.save(os.path.join(ASSETS_DIR, "attendance_form_banner.png"), quality=95)
    print("Generated attendance_form_banner.png")

if __name__ == "__main__":
    create_face_recognition_assets()
    create_attendance_assets()
    print("All Face Recognition & Attendance assets generated successfully!")
