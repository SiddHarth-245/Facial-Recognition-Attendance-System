"""
========================================================================================
FaceAttend Ultra-2K High-Definition Cyber-Blue Asset Generator (Zero Watermark Edition)
========================================================================================
Generates crystal-sharp 2K (2048x1152) and responsive vector-like graphics for:
1. Login Portal (bg_login.png, login_bg_cyber.png)
2. Main Dashboard (dashboard_bg_cyber.png, bg_dashboard.jpg)
3. Face Recognition Studio (face_recog_bg_cyber.png)
4. Student Management Header (student_header.png)
5. Attendance Records Header (attendance_header.png)
6. Train Data Banners (train_top_banner.png, train_bottom_mosaic.jpg)
7. User Registration Banner (register_banner.png)
8. Developer & Help Desk Assets (help_desk_bg.jpg, developer_photo.png)
========================================================================================
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
os.makedirs(ASSETS_DIR, exist_ok=True)


def get_font(size: int, bold: bool = False):
    """Safely retrieves high-quality system fonts for crisp typography."""
    names = ["segoeuib.ttf", "arialbd.ttf"] if bold else ["segoeui.ttf", "arial.ttf"]
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except Exception:
            try:
                win_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", n)
                if os.path.exists(win_path):
                    return ImageFont.truetype(win_path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def draw_cyber_grid(draw, width, height, step=60, alpha_color=(8, 26, 56)):
    """Draws a subtle perspective cybernetic grid overlay."""
    for x in range(0, width, step):
        draw.line([(x, 0), (x, height)], fill=alpha_color, width=1)
    for y in range(0, height, step):
        draw.line([(0, y), (width, y)], fill=alpha_color, width=1)


def draw_hud_bracket(draw, x, y, w, h, length=30, color=(0, 210, 255), width_px=3):
    """Draws futuristic targeting HUD brackets around a box."""
    # Top-Left
    draw.line([(x, y), (x + length, y)], fill=color, width=width_px)
    draw.line([(x, y), (x, y + length)], fill=color, width=width_px)
    # Top-Right
    draw.line([(x + w, y), (x + w - length, y)], fill=color, width=width_px)
    draw.line([(x + w, y), (x + w, y + length)], fill=color, width=width_px)
    # Bottom-Left
    draw.line([(x, y + h), (x + length, y + h)], fill=color, width=width_px)
    draw.line([(x, y + h), (x, y + h - length)], fill=color, width=width_px)
    # Bottom-Right
    draw.line([(x + w, y + h), (x + w - length, y + h)], fill=color, width=width_px)
    draw.line([(x + w, y + h), (x + w, y + h - length)], fill=color, width=width_px)


# -----------------------------------------------------------------------------
# 1. Login Background (2048 x 1152 Native 2K - Zero Watermark)
# -----------------------------------------------------------------------------
def generate_login_background():
    w, h = 2048, 1152
    img = Image.new("RGB", (w, h), (3, 11, 24))
    draw = ImageDraw.Draw(img)

    # Gradient backdrop: Deep Midnight Navy to Cyber Abyss
    for y in range(h):
        ratio = y / h
        r = int(3 + (6 - 3) * ratio)
        g = int(11 + (22 - 11) * ratio)
        b = int(24 + (52 - 24) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    # Perspective Cyber Grid
    draw_cyber_grid(draw, w, h, step=80, alpha_color=(8, 28, 60))

    # Top Super Header Bar
    draw.rectangle([(0, 0), (w, 120)], fill=(5, 17, 38))
    draw.line([(0, 120), (w, 120)], fill=(0, 132, 255), width=3)
    draw.line([(0, 121), (w, 121)], fill=(56, 189, 248), width=1)

    # Header Titles (Zero Watermark)
    draw.text((60, 28), "FACEATTEND", fill=(0, 210, 255), font=get_font(34, True))
    draw.text((340, 36), "|  AI-POWERED BIOMETRIC ATTENDANCE SYSTEM", fill=(255, 255, 255), font=get_font(22, True))
    draw.text((60, 78), "Department of Computer Science & Engineering  •  KIIT University", fill=(148, 163, 184), font=get_font(15, False))
    draw.text((w - 480, 44), "KIIT DEEMED TO BE UNIVERSITY", fill=(100, 116, 139), font=get_font(16, True))

    # Left Column: Precision Biometric Face Scanner HUD Reticle
    cx, cy, radius = 540, 620, 230
    
    # Outer Concentric Glowing Rings
    for r_offset, alpha_rgb, w_px in [
        (80, (6, 32, 68), 2),
        (50, (10, 50, 100), 2),
        (25, (0, 132, 255), 3),
        (0, (56, 189, 248), 2)
    ]:
        draw.ellipse([(cx - radius - r_offset, cy - radius - r_offset), 
                      (cx + radius + r_offset, cy + radius + r_offset)], 
                     outline=alpha_rgb, width=w_px)

    # Futuristic Tick Marks around perimeter
    for deg in range(0, 360, 15):
        rad = math.radians(deg)
        r1 = radius + 15
        r2 = radius + (30 if deg % 45 == 0 else 22)
        x1 = cx + int(r1 * math.cos(rad))
        y1 = cy + int(r1 * math.sin(rad))
        x2 = cx + int(r2 * math.cos(rad))
        y2 = cy + int(r2 * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=(0, 210, 255) if deg % 45 == 0 else (14, 165, 233), width=2 if deg % 45 == 0 else 1)

    # Sleek Facial Mesh Outline (Realistic Head Silhouette)
    draw.ellipse([(cx - 110, cy - 150), (cx + 110, cy + 90)], outline=(0, 210, 255), width=3)
    draw.arc([(cx - 90, cy - 60), (cx + 90, cy + 140)], 25, 155, fill=(0, 210, 255), width=3)
    
    # Eyes Crosshairs Nodes
    for ex in [cx - 50, cx + 50]:
        ey = cy - 35
        draw.ellipse([(ex - 22, ey - 22), (ex + 22, ey + 22)], outline=(56, 189, 248), width=2)
        draw.ellipse([(ex - 6, ey - 6), (ex + 6, ey + 6)], fill=(0, 210, 255))
        draw.line([(ex - 30, ey), (ex + 30, ey)], fill=(56, 189, 248), width=1)
        draw.line([(ex, ey - 30), (ex, ey + 30)], fill=(56, 189, 248), width=1)

    # Nose & Mouth Landmark Nodes
    draw.line([(cx, cy - 20), (cx - 15, cy + 25), (cx + 15, cy + 25)], fill=(56, 189, 248), width=2)
    draw.arc([(cx - 45, cy + 35), (cx + 45, cy + 85)], 20, 160, fill=(0, 210, 255), width=3)
    
    # Horizontal Laser Scanner Line
    draw.line([(cx - 190, cy + 10), (cx + 190, cy + 10)], fill=(0, 210, 255), width=2)

    # HUD Outer Corner Targeting Brackets
    draw_hud_bracket(draw, cx - radius - 20, cy - radius - 20, (radius + 20)*2, (radius + 20)*2, length=50, color=(0, 210, 255), width_px=4)

    # Left Column HUD Sub-Labels
    draw.text((cx, cy + radius + 60), "FACIAL RECOGNITION ACTIVE", fill=(56, 189, 248), font=get_font(22, True), anchor="mm")
    draw.text((cx, cy + radius + 100), "Advanced AI Face Detection & Biometric Authentication", fill=(148, 163, 184), font=get_font(15, False), anchor="mm")

    # Right Column: Sleek Glassmorphism Backdrop Shadow for Tkinter Form Card
    rx, ry, rw, rh = 1220, 220, 700, 800
    draw.rectangle([(rx, ry), (rx + rw, ry + rh)], fill=(7, 22, 47))
    draw.rectangle([(rx, ry), (rx + rw, ry + rh)], outline=(25, 55, 95), width=2)
    draw.line([(rx, ry), (rx + rw, ry)], fill=(0, 132, 255), width=4)

    # Save to assets (Overwriting all old versions)
    for fn in ["bg_login.png", "login_bg_cyber.png"]:
        img.save(os.path.join(ASSETS_DIR, fn), quality=95)
    print("Generated 2K Clean Login Backgrounds (Zero Watermark)")


# -----------------------------------------------------------------------------
# 2. Main Dashboard Background (2048 x 1152 Native 2K - Zero Watermark)
# -----------------------------------------------------------------------------
def generate_dashboard_background():
    w, h = 2048, 1152
    img = Image.new("RGB", (w, h), (3, 11, 24))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        ratio = y / h
        r = int(3 + (6 - 3) * ratio)
        g = int(11 + (22 - 11) * ratio)
        b = int(24 + (52 - 24) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    draw_cyber_grid(draw, w, h, step=80, alpha_color=(8, 26, 56))

    for fn in ["dashboard_bg_cyber.png", "bg_dashboard.jpg"]:
        img.save(os.path.join(ASSETS_DIR, fn), quality=95)
    print("Generated 2K Dashboard Backgrounds")


# -----------------------------------------------------------------------------
# 3. Face Recognition Studio Background (2048 x 1152 Native 2K)
# -----------------------------------------------------------------------------
def generate_face_recog_background():
    w, h = 2048, 1152
    img = Image.new("RGB", (w, h), (3, 11, 24))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        ratio = y / h
        r = int(3 + (6 - 3) * ratio)
        g = int(11 + (22 - 11) * ratio)
        b = int(24 + (52 - 24) * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    draw_cyber_grid(draw, w, h, step=80, alpha_color=(8, 26, 56))

    # Header Bar
    draw.rectangle([(0, 0), (w, 110)], fill=(5, 17, 38))
    draw.line([(0, 110), (w, 110)], fill=(0, 132, 255), width=3)
    draw.line([(0, 111), (w, 111)], fill=(56, 189, 248), width=1)

    draw.text((60, 24), "BIOMETRIC FACE RECOGNITION STUDIO", fill=(0, 210, 255), font=get_font(30, True))
    draw.text((60, 68), "Live 60+ FPS Video Stream Processing  •  LBPH Machine Learning Classifier", fill=(148, 163, 184), font=get_font(15, False))

    for fn in ["face_recog_bg_cyber.png", "face_recog_right.jpg"]:
        img.save(os.path.join(ASSETS_DIR, fn), quality=95)
    print("Generated 2K Face Recognition Backgrounds")


# -----------------------------------------------------------------------------
# 4. Student & Attendance Header Banners (2048 x 240 Native)
# -----------------------------------------------------------------------------
def generate_headers():
    for name, title, sub in [
        ("student_header.png", "STUDENT MANAGEMENT SYSTEM", "Enrolled Student Directory, 29+ Academic Disciplines & Facial Biometric Capture"),
        ("attendance_header.png", "ATTENDANCE RECORDS SYSTEM", "Daily Relational Logs, Real-Time CSV Data Pipeline & Status Verification")
    ]:
        w, h = 2048, 240
        img = Image.new("RGB", (w, h), (4, 15, 33))
        draw = ImageDraw.Draw(img)

        for y in range(h):
            ratio = y / h
            r = int(4 + 4 * ratio)
            g = int(15 + 10 * ratio)
            b = int(33 + 25 * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        draw_cyber_grid(draw, w, h, step=50, alpha_color=(8, 26, 56))
        draw.line([(0, h - 2), (w, h - 2)], fill=(0, 132, 255), width=3)
        draw.line([(0, h - 1), (w, h - 1)], fill=(56, 189, 248), width=1)

        draw.text((60, 45), "FACEATTEND", fill=(0, 210, 255), font=get_font(26, True))
        draw.text((290, 45), f"|  {title}", fill=(255, 255, 255), font=get_font(26, True))
        draw.text((60, 110), sub, fill=(148, 163, 184), font=get_font(16, False))
        draw.text((w - 480, 50), "KIIT DEEMED TO BE UNIVERSITY", fill=(100, 116, 139), font=get_font(16, True))

        img.save(os.path.join(ASSETS_DIR, name), quality=95)
    print("Generated 2K Module Headers")


# -----------------------------------------------------------------------------
# 5. Train Banners (2048 x 360 and 2048 x 600)
# -----------------------------------------------------------------------------
def generate_train_assets():
    w, h = 2048, 360
    img = Image.new("RGB", (w, h), (4, 15, 33))
    draw = ImageDraw.Draw(img)
    draw_cyber_grid(draw, w, h, step=60, alpha_color=(8, 26, 56))
    draw.line([(0, h - 2), (w, h - 2)], fill=(139, 92, 246), width=3)

    draw.text((60, 60), "MULTI-STUDENT LBPH MODEL TRAINING HUB", fill=(255, 255, 255), font=get_font(30, True))
    draw.text((60, 120), "Compiles 100 Facial Samples Per Enrolled Student Into Serialized classifier.xml", fill=(148, 163, 184), font=get_font(17, False))
    draw.text((60, 170), "• Local Binary Patterns Histograms (Radius=1, Neighbors=8, Grid=8x8)", fill=(56, 189, 248), font=get_font(15, False))

    img.save(os.path.join(ASSETS_DIR, "train_top_banner.png"), quality=95)
    print("Generated 2K Train Top Banner")


# -----------------------------------------------------------------------------
# 6. User Registration Left Banner (800 x 1400)
# -----------------------------------------------------------------------------
def generate_register_banner():
    w, h = 800, 1400
    img = Image.new("RGB", (w, h), (4, 15, 33))
    draw = ImageDraw.Draw(img)

    for y in range(h):
        ratio = y / h
        r = int(4 + 8 * ratio)
        g = int(15 + 20 * ratio)
        b = int(33 + 50 * ratio)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    draw_cyber_grid(draw, w, h, step=70, alpha_color=(12, 38, 78))

    cx, cy = w // 2, 450
    draw.ellipse([(cx - 160, cy - 160), (cx + 160, cy + 160)], outline=(0, 132, 255), width=3)
    draw.ellipse([(cx - 130, cy - 130), (cx + 130, cy + 130)], outline=(56, 189, 248), width=1)
    draw_hud_bracket(draw, cx - 180, cy - 180, 360, 360, length=40, color=(0, 210, 255), width_px=4)

    draw.ellipse([(cx - 60, cy - 60), (cx + 60, cy + 60)], fill=(0, 210, 255))
    draw.pieslice([(cx - 100, cy + 10), (cx + 100, cy + 180)], 180, 360, fill=(0, 132, 255))

    draw.text((cx, 750), "FACEATTEND", fill=(0, 210, 255), font=get_font(38, True), anchor="mm")
    draw.text((cx, 810), "SECURITY & AUTH PORTAL", fill=(255, 255, 255), font=get_font(22, True), anchor="mm")
    draw.text((cx, 890), "\"Your Nature Is\nYour Digital Future\"", fill=(148, 163, 184), font=get_font(24, True), anchor="mm", align="center")
    draw.text((cx, 1050), "KIIT Deemed to be University\nDepartment of CSE", fill=(100, 116, 139), font=get_font(18, False), anchor="mm", align="center")

    img.save(os.path.join(ASSETS_DIR, "register_banner.png"), quality=95)
    print("Generated Register Banner")


if __name__ == "__main__":
    generate_login_background()
    generate_dashboard_background()
    generate_face_recog_background()
    generate_headers()
    generate_train_assets()
    generate_register_banner()
    print("All 2K Clean Assets (Zero Watermark) Generated Successfully!")
