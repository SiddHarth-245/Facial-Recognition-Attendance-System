"""
Enhanced Asset Generator for Facial Recognition Attendance Management System.
Generates realistic UI graphics, scenic dashboard background, button tiles,
header collages, and classroom banners matching the exact UI screenshots.
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_DIR = os.path.join(ASSETS_DIR, "icons")
os.makedirs(ICONS_DIR, exist_ok=True)

def get_font(size: int, bold: bool = False):
    """Loads system fonts safely."""
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

# ----------------- 1. Scenic Night Moon Lake Dashboard Background -----------------
def create_dashboard_background(width: int = 1366, height: int = 768, filename: str = "bg_dashboard.jpg"):
    """Generates scenic purple-blue night lake with giant glowing moon matching Image 1."""
    img = Image.new("RGB", (width, height), color=(15, 10, 35))
    draw = ImageDraw.Draw(img)
    
    # Sky Gradient: Deep space purple to twilight indigo
    for y in range(height):
        ratio = y / height
        if ratio < 0.65:
            # Sky
            r = int(20 + (50 - 20) * (ratio / 0.65))
            g = int(12 + (35 - 12) * (ratio / 0.65))
            b = int(45 + (110 - 45) * (ratio / 0.65))
        else:
            # Lake Water
            w_ratio = (ratio - 0.65) / 0.35
            r = int(18 + 15 * w_ratio)
            g = int(28 + 25 * w_ratio)
            b = int(60 + 40 * w_ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # Draw Giant Glowing Moon on top right
    mx, my, mr = width - 160, 200, 160
    for gr in range(mr + 80, mr, -4):
        alpha = int(40 * (1 - (gr - mr) / 80))
        draw.ellipse([mx - gr, my - gr, mx + gr, my + gr], fill=(r + alpha, g + alpha, b + alpha * 2))
    
    # Moon surface
    draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(235, 240, 255))
    # Moon craters / texture
    crater_draw = ImageDraw.Draw(img)
    craters = [(mx - 40, my - 30, 35), (mx + 30, my - 60, 25), (mx - 20, my + 40, 45), (mx + 50, my + 20, 30), (mx - 70, my + 10, 20)]
    for cx, cy, cr in craters:
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill=(210, 218, 240))

    # Distant Mountains
    mountains = [(0, 480), (180, 390), (380, 450), (600, 370), (850, 460), (1050, 380), (1200, 420), (width, 470)]
    draw.polygon(mountains + [(width, height), (0, height)], fill=(12, 18, 42))

    # Water reflections & ripples
    for y in range(int(height * 0.65), height, 4):
        for x in range(0, width, 18):
            if (x + y) % 7 == 0:
                draw.line([(x, y), (x + 12, y)], fill=(40, 80, 140))
            if abs(x - mx) < 180 and y % 6 == 0:
                # Moon shimmer in water
                draw.line([(x - 8, y), (x + 8, y)], fill=(180, 210, 255))

    img.save(os.path.join(ASSETS_DIR, filename), quality=95)
    print(f"Generated {filename}")

# ----------------- 2. Top Header Banner with Faces & Title -----------------
def create_main_header(width: int = 1366, height: int = 145, filename: str = "main_header.png"):
    """Generates the dual-tier header: top montage strip + title bar with clock."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Top strip (Height: 85) - AI Facial Recognition Collage
    strip_h = 85
    # Segment 1: Left Tech Banner ("BEST FACIAL RECOGNITION SOFTWARE")
    seg1_w = int(width * 0.26)
    draw.rectangle([0, 0, seg1_w, strip_h], fill=(5, 15, 35))
    # Draw wireframe face silhouette on left
    draw.ellipse([seg1_w//2 - 28, strip_h//2 - 28, seg1_w//2 + 28, strip_h//2 + 28], outline=(0, 210, 255), width=2)
    draw.text((15, 12), "BEST", fill=(255, 255, 255), font=get_font(12, True))
    draw.text((15, 28), "FACIAL", fill=(0, 220, 255), font=get_font(18, True))
    draw.text((15, 48), "RECOGNITION", fill=(255, 255, 255), font=get_font(14, True))
    draw.text((15, 66), "SOFTWARE", fill=(150, 200, 240), font=get_font(10, True))

    # Segments 2, 3, 4: 3 Face detection scan boxes (as shown in Image 1)
    face_colors = [(25, 45, 80), (30, 55, 95), (20, 50, 85)]
    scan_colors = [(255, 170, 0), (255, 220, 0), (0, 200, 255)]
    seg_face_w = int((width * 0.44) / 3)
    
    for i in range(3):
        fx1 = seg1_w + i * seg_face_w
        fx2 = fx1 + seg_face_w
        draw.rectangle([fx1, 0, fx2, strip_h], fill=face_colors[i])
        # Face representation
        fcx, fcy = (fx1 + fx2) // 2, strip_h // 2
        draw.ellipse([fcx - 18, fcy - 24, fcx + 18, fcy + 12], fill=(225, 200, 185))
        draw.pieslice([fcx - 26, fcy + 12, fcx + 26, fcy + 42], 180, 360, fill=(180, 190, 210))
        
        # Scan target bracket
        bw = 28
        sc = scan_colors[i]
        bx1, by1, bx2, by2 = fcx - bw, fcy - bw, fcx + bw, fcy + bw
        c_len = 8
        draw.line([(bx1, by1), (bx1 + c_len, by1)], fill=sc, width=3)
        draw.line([(bx1, by1), (bx1, by1 + c_len)], fill=sc, width=3)
        draw.line([(bx2, by1), (bx2 - c_len, by1)], fill=sc, width=3)
        draw.line([(bx2, by1), (bx2, by1 + c_len)], fill=sc, width=3)
        draw.line([(bx1, by2), (bx1 + c_len, by2)], fill=sc, width=3)
        draw.line([(bx1, by2), (bx1, by2 - c_len)], fill=sc, width=3)
        draw.line([(bx2, by2), (bx2 - c_len, by2)], fill=sc, width=3)
        draw.line([(bx2, by2), (bx2, by2 - c_len)], fill=sc, width=3)

    # Segment 5: Right AI Network HUD
    seg5_x = seg1_w + 3 * seg_face_w
    draw.rectangle([seg5_x, 0, width, strip_h], fill=(8, 22, 50))
    # HUD circle & nodes
    draw.ellipse([seg5_x + 40, 15, seg5_x + 95, 70], outline=(0, 220, 255), width=2)
    draw.ellipse([seg5_x + 50, 25, seg5_x + 85, 60], outline=(0, 180, 230), width=1)
    draw.line([(seg5_x + 95, 42), (seg5_x + 180, 42)], fill=(0, 220, 255), width=2)

    # Top Developer watermark on left
    draw.text((10, 3), "Developed By: CodeWithKiran", fill=(255, 255, 255), font=get_font(11, True))

    # Bottom Title Bar (Height: 60)
    draw.rectangle([0, strip_h, width, height], fill=(255, 255, 255))
    draw.line([(0, strip_h), (width, strip_h)], fill=(180, 20, 20), width=2)
    draw.line([(0, height - 1), (width, height - 1)], fill=(210, 210, 210), width=1)

    # Big Bold Red Title
    title_text = "FACE RECOGNITION ATTENDANCE SYSTEM SOFTWARE"
    font_title = get_font(26, bold=True)
    try:
        bbox = draw.textbbox((0, 0), title_text, font=font_title)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    except Exception:
        tw, th = 850, 30

    draw.text(((width - tw) // 2, strip_h + (height - strip_h - th) // 2 - 2), title_text, fill=(200, 15, 15), font=font_title)

    img.save(os.path.join(ASSETS_DIR, filename), quality=95)
    print(f"Generated {filename}")

# ----------------- 3. Student Management System Header Banner -----------------
def create_student_header(width: int = 1366, height: int = 145, filename: str = "student_header.png"):
    """Generates the student header banner with classroom collage & student management title."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    strip_h = 85
    # Classroom / Students collage strip
    colors = [(70, 90, 120), (50, 80, 110), (80, 60, 95), (60, 90, 100), (90, 75, 60), (45, 75, 110)]
    w_seg = width // 6
    for i in range(6):
        x1 = i * w_seg
        x2 = (i + 1) * w_seg if i < 5 else width
        draw.rectangle([x1, 0, x2, strip_h], fill=colors[i])
        
        # Classroom students silhouettes
        cx, cy = (x1 + x2) // 2, strip_h // 2 + 5
        draw.ellipse([cx - 14, cy - 20, cx + 14, cy + 8], fill=(230, 210, 195))
        draw.pieslice([cx - 22, cy + 8, cx + 22, cy + 35], 180, 360, fill=(200, 220, 240))
        
        # Detection box
        if i in [0, 1, 3, 5]:
            draw.rectangle([cx - 20, cy - 26, cx + 20, cy + 14], outline=(0, 255, 160) if i % 2 == 0 else (0, 220, 255), width=2)

    # Sub-bar (Height: 60)
    draw.rectangle([0, strip_h, width, height], fill=(255, 255, 255))
    draw.line([(0, strip_h), (width, strip_h)], fill=(0, 70, 180), width=2)

    # University Seal / Emblem Icon on left of title
    emblem_x = width // 2 - 280
    draw.ellipse([emblem_x - 18, strip_h + 12, emblem_x + 18, strip_h + 48], fill=(20, 35, 70), outline=(220, 170, 20), width=2)
    draw.text((emblem_x - 8, strip_h + 18), "🎓", font=get_font(18))

    # Title
    title_text = "STUDENT MANAGEMENT SYSTEM"
    font_title = get_font(26, bold=True)
    draw.text((emblem_x + 30, strip_h + 14), title_text, fill=(15, 60, 150), font=font_title)

    img.save(os.path.join(ASSETS_DIR, filename), quality=95)
    print(f"Generated {filename}")

# ----------------- 4. Dashboard 8 Button Tile Graphics -----------------
def create_dashboard_button_tiles():
    """Generates the 8 exact photographic button cards matching Screenshots 1 & 5."""
    tile_w, tile_h = 240, 190
    banner_h = 32

    tiles = [
        # (filename, bg_gradient_start, bg_gradient_end, title_text, icon_type)
        ("tile_student.png", (35, 55, 80), (15, 30, 50), "STUDENT DETAILS", "students_study"),
        ("tile_face.png", (10, 35, 65), (5, 18, 38), "FACE RECOGNITION", "biometric_scan"),
        ("tile_attendance.png", (12, 45, 70), (8, 25, 45), "ATTENDANCE", "terminal_clock"),
        ("tile_help.png", (18, 75, 125), (10, 48, 85), "HELP", "help_desk_agents"),
        ("tile_train.png", (15, 25, 55), (8, 15, 35), "TRAIN DATA", "wireframe_mesh"),
        ("tile_photos.png", (45, 65, 90), (25, 40, 60), "PHOTOS", "group_selfie"),
        ("tile_developer.png", (8, 38, 75), (4, 20, 45), "DEVELOPER", "hologram_ui"),
        ("tile_exit.png", (20, 30, 50), (10, 18, 32), "EXIT", "exit_sphere"),
    ]

    for filename, c_top, c_bot, label, itype in tiles:
        img = Image.new("RGB", (tile_w, tile_h), color=c_top)
        draw = ImageDraw.Draw(img)

        # Gradient Image Area
        img_area_h = tile_h - banner_h
        for y in range(img_area_h):
            r = int(c_top[0] + (c_bot[0] - c_top[0]) * (y / img_area_h))
            g = int(c_top[1] + (c_bot[1] - c_top[1]) * (y / img_area_h))
            b = int(c_top[2] + (c_bot[2] - c_top[2]) * (y / img_area_h))
            draw.line([(0, y), (tile_w, y)], fill=(r, g, b))

        cx, cy = tile_w // 2, img_area_h // 2

        # Draw specific visual theme for each button
        if itype == "students_study":
            # 3 students around a table studying
            draw.ellipse([cx - 50, cy - 25, cx - 20, cy + 5], fill=(225, 200, 185))
            draw.pieslice([cx - 65, cy + 5, cx - 5, cy + 50], 180, 360, fill=(180, 80, 90))
            draw.ellipse([cx - 15, cy - 35, cx + 15, cy - 5], fill=(220, 195, 180))
            draw.pieslice([cx - 30, cy - 5, cx + 30, cy + 45], 180, 360, fill=(40, 120, 180))
            draw.ellipse([cx + 20, cy - 25, cx + 50, cy + 5], fill=(230, 205, 190))
            draw.pieslice([cx + 5, cy + 5, cx + 65, cy + 50], 180, 360, fill=(80, 160, 100))
            draw.rectangle([cx - 80, cy + 30, cx + 80, cy + 55], fill=(160, 120, 80)) # table
            draw.rectangle([cx - 20, cy + 25, cx + 20, cy + 40], fill=(240, 240, 240)) # book
        elif itype == "biometric_scan":
            # Futuristic man face with biometric circle scanner
            draw.ellipse([cx - 35, cy - 40, cx + 35, cy + 30], fill=(210, 190, 175))
            draw.ellipse([cx + 5, cy - 18, cx + 45, cy + 22], outline=(0, 240, 255), width=3)
            draw.ellipse([cx + 12, cy - 11, cx + 38, cy + 15], outline=(0, 180, 255), width=1)
            draw.line([(cx - 10, cy + 2), (cx + 60, cy + 2)], fill=(0, 255, 220), width=2)
        elif itype == "terminal_clock":
            # Biometric attendance machine
            draw.rectangle([cx - 35, cy - 55, cx + 35, cy + 50], fill=(45, 55, 70), outline=(0, 210, 255), width=2)
            draw.rectangle([cx - 25, cy - 45, cx + 25, cy - 5], fill=(10, 20, 35)) # screen
            draw.ellipse([cx - 12, cy - 38, cx + 12, cy - 14], fill=(0, 200, 255)) # face scan icon
            draw.rectangle([cx - 18, cy + 8, cx + 18, cy + 38], fill=(20, 30, 45), outline=(0, 255, 150))
            draw.text((cx - 40, cy - 70), "New Attendance", fill=(200, 230, 255), font=get_font(9, True))
        elif itype == "help_desk_agents":
            # Help Desk headset agents
            draw.ellipse([cx - 28, cy - 25, cx + 28, cy + 31], fill=(255, 255, 255))
            draw.pieslice([cx - 45, cy + 18, cx + 45, cy + 68], 180, 360, fill=(255, 255, 255))
            draw.arc([cx - 36, cy - 30, cx + 36, cy + 20], 160, 380, fill=(20, 50, 90), width=6) # Headset
            draw.ellipse([cx - 40, cy - 5, cx - 28, cy + 12], fill=(20, 50, 90))
            draw.ellipse([cx + 28, cy - 5, cx + 40, cy + 12], fill=(20, 50, 90))
            draw.line([(cx + 34, cy + 6), (cx + 10, cy + 20)], fill=(20, 50, 90), width=4)
            draw.text((cx - 42, cy - 52), "HELP DESK", fill=(255, 255, 255), font=get_font(13, True))
        elif itype == "wireframe_mesh":
            # 3D green/cyan wireframe head
            draw.ellipse([cx - 36, cy - 45, cx + 36, cy + 35], outline=(0, 255, 180), width=2)
            for rad in range(10, 40, 10):
                draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(0, 200, 240), width=1)
            for ang in range(0, 180, 30):
                r = math.radians(ang)
                draw.line([(cx - int(36 * math.cos(r)), cy - int(45 * math.sin(r))),
                           (cx + int(36 * math.cos(r)), cy + int(45 * math.sin(r)))], fill=(0, 180, 220), width=1)
        elif itype == "group_selfie":
            # Group selfie with face bounding boxes
            faces_pos = [(cx - 40, cy - 20), (cx, cy - 30), (cx + 45, cy - 15), (cx - 20, cy + 15), (cx + 25, cy + 20)]
            for fx, fy in faces_pos:
                draw.ellipse([fx - 14, fy - 14, fx + 14, fy + 14], fill=(225, 195, 180))
                draw.rectangle([fx - 18, fy - 18, fx + 18, fy + 18], outline=(0, 255, 0), width=2)
        elif itype == "hologram_ui":
            # Developer hologram multi-monitor screens
            draw.rectangle([cx - 45, cy - 35, cx + 45, cy + 25], outline=(0, 220, 255), width=2, fill=(10, 30, 60))
            draw.rectangle([cx - 38, cy - 28, cx - 5, cy - 2], fill=(0, 180, 230))
            draw.rectangle([cx + 5, cy - 28, cx + 38, cy - 2], fill=(255, 100, 100))
            draw.rectangle([cx - 38, cy + 5, cx + 38, cy + 18], fill=(0, 220, 140))
        elif itype == "exit_sphere":
            # Big 3D glossy circular EXIT button
            r = 45
            for gr in range(r, 0, -2):
                ratio = gr / r
                cr = int(10 + 30 * ratio)
                cg = int(70 + 80 * ratio)
                cb = int(180 + 75 * ratio)
                draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=(cr, cg, cb))
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 255, 255), width=3)
            font_exit = get_font(18, True)
            draw.text((cx - 20, cy - 12), "EXIT", fill=(255, 255, 255), font=font_exit)

        # Bottom Dark Blue Label Strip (Height: 32)
        draw.rectangle([0, tile_h - banner_h, tile_w, tile_h], fill=(0, 10, 90))
        draw.line([(0, tile_h - banner_h), (tile_w, tile_h - banner_h)], fill=(0, 120, 220), width=2)
        
        font_lbl = get_font(11, True)
        try:
            bbox = draw.textbbox((0, 0), label, font=font_lbl)
            tw = bbox[2] - bbox[0]
        except Exception:
            tw = 90
        draw.text(((tile_w - tw) // 2, tile_h - banner_h + 7), label, fill=(255, 255, 255), font=font_lbl)

        img.save(os.path.join(ASSETS_DIR, filename), quality=95)
        print(f"Generated {filename}")

# ----------------- 5. Student Form & Details Embedded Banners -----------------
def create_student_internal_banners():
    """Generates internal classroom banners inside Student Management System."""
    # Top classroom kids raising hands (380x110)
    img1 = Image.new("RGB", (380, 110), color=(240, 245, 250))
    d1 = ImageDraw.Draw(img1)
    for i in range(4):
        cx = 50 + i * 90
        # Student raising hand
        d1.ellipse([cx - 16, 35, cx + 16, 67], fill=(230, 205, 190))
        d1.pieslice([cx - 26, 67, cx + 26, 120], 180, 360, fill=(220, 90, 100) if i%2==0 else (60, 140, 200))
        # Raised arm
        d1.line([(cx + 12, 60), (cx + 25, 20)], fill=(230, 205, 190), width=6)
    d1.rectangle([0, 90, 380, 110], fill=(160, 120, 80)) # classroom desk
    img1.save(os.path.join(ASSETS_DIR, "student_form_top.png"))

    # Bottom students montage (380x65)
    img2 = Image.new("RGB", (380, 65), color=(20, 40, 70))
    d2 = ImageDraw.Draw(img2)
    for i in range(5):
        cx = 38 + i * 75
        d2.ellipse([cx - 12, 10, cx + 12, 34], fill=(225, 200, 185))
        d2.pieslice([cx - 18, 34, cx + 18, 70], 180, 360, fill=(70 + i*20, 100 + i*15, 150))
    img2.save(os.path.join(ASSETS_DIR, "student_form_bottom.png"))

    # Right panel library study group (600x120)
    img3 = Image.new("RGB", (600, 120), color=(30, 45, 65))
    d3 = ImageDraw.Draw(img3)
    # Background chalkboard/bookshelf
    d3.rectangle([0, 0, 600, 45], fill=(20, 30, 45))
    # 4 College students studying around laptops
    for i in range(4):
        cx = 80 + i * 140
        d3.ellipse([cx - 20, 25, cx + 20, 65], fill=(230, 205, 190))
        d3.pieslice([cx - 32, 65, cx + 32, 130], 180, 360, fill=(180 - i*20, 60 + i*30, 120))
        # Laptop
        d3.rectangle([cx - 18, 90, cx + 18, 110], fill=(200, 210, 225))
    img3.save(os.path.join(ASSETS_DIR, "student_details_banner.png"))
    print("Generated student internal banners!")

if __name__ == "__main__":
    create_dashboard_background()
    create_main_header()
    create_student_header()
    create_dashboard_button_tiles()
    create_student_internal_banners()
    print("All enhanced assets generated successfully!")
