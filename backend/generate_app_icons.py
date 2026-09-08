import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def create_master_icon(size=1024):
    # Create 2x resolution for super-sampled anti-aliasing
    S = 2
    dim = size * S
    cx, cy = dim / 2.0, dim / 2.0
    
    # 1. Base Image
    img = Image.new('RGBA', (dim, dim), (0, 0, 0, 0))
    
    # 2. Ambient emerald/cyan glow
    glow = Image.new('RGBA', (dim, dim), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)
    for r in range(int(460 * S), int(340 * S), -int(15 * S)):
        alpha = int(50 * (1.0 - (r - 340 * S) / (120.0 * S)))
        gdraw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 185, 129, alpha))
    glow = glow.filter(ImageFilter.GaussianBlur(int(30 * S)))
    img = Image.alpha_composite(img, glow)
    
    # 3. Squircle container background
    margin = int(105 * S)
    radius = int(215 * S)
    rect = [margin, margin, dim - margin, dim - margin]
    
    # Create gradient array using numpy (instantaneous)
    y_coords = np.linspace(0, 1, dim)
    # Slate gradient from #0E172A (14, 23, 42) to #020617 (2, 6, 23)
    r_chan = (14 * (1 - y_coords) + 2 * y_coords).astype(np.uint8)
    g_chan = (23 * (1 - y_coords) + 6 * y_coords).astype(np.uint8)
    b_chan = (42 * (1 - y_coords) + 23 * y_coords).astype(np.uint8)
    
    rgb_grad = np.dstack([
        np.tile(r_chan[:, np.newaxis], (1, dim)),
        np.tile(g_chan[:, np.newaxis], (1, dim)),
        np.tile(b_chan[:, np.newaxis], (1, dim)),
        np.full((dim, dim), 255, dtype=np.uint8)
    ])
    sq_bg = Image.fromarray(rgb_grad, mode='RGBA')
    
    sq_mask = Image.new('L', (dim, dim), 0)
    ImageDraw.Draw(sq_mask).rounded_rectangle(rect, radius=radius, fill=255)
    sq_bg.putalpha(sq_mask)
    img = Image.alpha_composite(img, sq_bg)
    
    # Squircle border stroke
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(rect, radius=radius, outline=(16, 185, 129, 210), width=int(12 * S))
    
    # 4. Shield
    shield_w = int(245 * S)
    shield_top = int(245 * S)
    shield_mid_y = int(585 * S)
    shield_bottom = int(800 * S)
    shield_shoulder_y = int(340 * S)

    shield_pts = [
        (cx, shield_top),
        (cx + shield_w, shield_shoulder_y),
        (cx + int(shield_w * 0.92), shield_mid_y),
        (cx, shield_bottom),
        (cx - int(shield_w * 0.92), shield_mid_y),
        (cx - shield_w, shield_shoulder_y),
    ]

    shield_mask = Image.new('L', (dim, dim), 0)
    ImageDraw.Draw(shield_mask).polygon(shield_pts, fill=255)

    # Shield Gradient: Emerald (#059669) -> Cyan (#06B6D4)
    s_r = (5 * (1 - y_coords) + 6 * y_coords).astype(np.uint8)
    s_g = (150 * (1 - y_coords) + 182 * y_coords).astype(np.uint8)
    s_b = (105 * (1 - y_coords) + 212 * y_coords).astype(np.uint8)
    s_grad = np.dstack([
        np.tile(s_r[:, np.newaxis], (1, dim)),
        np.tile(s_g[:, np.newaxis], (1, dim)),
        np.tile(s_b[:, np.newaxis], (1, dim)),
        np.full((dim, dim), 255, dtype=np.uint8)
    ])
    shield_img = Image.fromarray(s_grad, mode='RGBA')
    shield_img.putalpha(shield_mask)
    img = Image.alpha_composite(img, shield_img)

    draw = ImageDraw.Draw(img)
    draw.polygon(shield_pts, outline=(255, 255, 255, 235), width=int(10 * S))

    # 5. Legal Metrology Beam & Scale
    # Central beam
    draw.line([(cx, int(345 * S)), (cx, int(695 * S))], fill=(255, 255, 255, 255), width=int(16 * S))
    # Top bar
    draw.line([(cx - int(145 * S), int(415 * S)), (cx + int(145 * S), int(415 * S))], fill=(255, 255, 255, 255), width=int(16 * S))
    # Base
    draw.line([(cx - int(75 * S), int(685 * S)), (cx + int(75 * S), int(685 * S))], fill=(255, 255, 255, 255), width=int(16 * S))
    draw.arc([cx - int(75 * S), int(655 * S), cx + int(75 * S), int(715 * S)], start=0, end=180, fill=(255, 255, 255, 255), width=int(16 * S))

    # Left dish
    draw.line([(cx - int(135 * S), int(415 * S)), (cx - int(175 * S), int(505 * S))], fill=(255, 255, 255, 220), width=int(6 * S))
    draw.line([(cx - int(135 * S), int(415 * S)), (cx - int(95 * S), int(505 * S))], fill=(255, 255, 255, 220), width=int(6 * S))
    draw.line([(cx - int(185 * S), int(520 * S)), (cx - int(85 * S), int(520 * S))], fill=(255, 255, 255, 255), width=int(10 * S))
    draw.arc([cx - int(185 * S), int(495 * S), cx - int(85 * S), int(545 * S)], start=0, end=180, fill=(255, 255, 255, 255), width=int(10 * S))

    # Right dish
    draw.line([(cx + int(135 * S), int(415 * S)), (cx + int(95 * S), int(505 * S))], fill=(255, 255, 255, 220), width=int(6 * S))
    draw.line([(cx + int(135 * S), int(415 * S)), (cx + int(175 * S), int(505 * S))], fill=(255, 255, 255, 220), width=int(6 * S))
    draw.line([(cx + int(85 * S), int(520 * S)), (cx + int(185 * S), int(520 * S))], fill=(255, 255, 255, 255), width=int(10 * S))
    draw.arc([cx + int(85 * S), int(495 * S), cx + int(185 * S), int(545 * S)], start=0, end=180, fill=(255, 255, 255, 255), width=int(10 * S))

    # 6. Verification Gold Checkmark
    check_start = (cx - int(90 * S), int(540 * S))
    check_vertex = (cx - int(20 * S), int(615 * S))
    check_end = (cx + int(115 * S), int(455 * S))

    # Checkmark glow
    for o in range(int(8 * S), -1, -int(2 * S)):
        alpha = int(45 * (1.0 - o / (8.0 * S)))
        draw.line([check_start, check_vertex], fill=(245, 158, 11, alpha), width=int((28 + o*2) * S))
        draw.line([check_vertex, check_end], fill=(245, 158, 11, alpha), width=int((28 + o*2) * S))

    # Core checkmark
    draw.line([check_start, check_vertex], fill=(253, 224, 71, 255), width=int(26 * S))
    draw.line([check_vertex, check_end], fill=(253, 224, 71, 255), width=int(26 * S))
    # Cap dots
    draw.ellipse([check_start[0] - int(12 * S), check_start[1] - int(12 * S), check_start[0] + int(12 * S), check_start[1] + int(12 * S)], fill=(253, 224, 71, 255))
    draw.ellipse([check_end[0] - int(12 * S), check_end[1] - int(12 * S), check_end[0] + int(12 * S), check_end[1] + int(12 * S)], fill=(253, 224, 71, 255))
    draw.ellipse([check_vertex[0] - int(12 * S), check_vertex[1] - int(12 * S), check_vertex[0] + int(12 * S), check_vertex[1] + int(12 * S)], fill=(253, 224, 71, 255))

    # Downscale with high-quality Lanczos resampling
    final_icon = img.resize((size, size), Image.Resampling.LANCZOS)
    return final_icon

def export_all_icons(base_dir):
    master = create_master_icon(1024)
    master.save(os.path.join(base_dir, "master_icon.png"))
    print("Saved master_icon.png (1024x1024)")
    
    flutter_dir = os.path.join(base_dir, "frontend_flutter")
    
    # 1. Android Mipmap icons
    android_res = os.path.join(flutter_dir, "android", "app", "src", "main", "res")
    android_sizes = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
    }
    for folder, px in android_sizes.items():
        target_folder = os.path.join(android_res, folder)
        os.makedirs(target_folder, exist_ok=True)
        resized = master.resize((px, px), Image.Resampling.LANCZOS)
        out_path = os.path.join(target_folder, "ic_launcher.png")
        resized.save(out_path)
        print(f"Updated Android {folder}/ic_launcher.png ({px}x{px})")

    # 2. Web Favicon and PWA icons
    web_dir = os.path.join(flutter_dir, "web")
    if os.path.exists(web_dir):
        favicon = master.resize((64, 64), Image.Resampling.LANCZOS)
        favicon.save(os.path.join(web_dir, "favicon.png"))
        print("Updated web/favicon.png (64x64)")
        
        icons_dir = os.path.join(web_dir, "icons")
        os.makedirs(icons_dir, exist_ok=True)
        master.resize((192, 192), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "Icon-192.png"))
        master.resize((512, 512), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "Icon-512.png"))
        master.resize((192, 192), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "Icon-maskable-192.png"))
        master.resize((512, 512), Image.Resampling.LANCZOS).save(os.path.join(icons_dir, "Icon-maskable-512.png"))
        print("Updated web/icons/ (192, 512, maskable)")

    # 3. iOS AppIcon set
    ios_icons = os.path.join(flutter_dir, "ios", "Runner", "Assets.xcassets", "AppIcon.appiconset")
    if os.path.exists(ios_icons):
        for f in os.listdir(ios_icons):
            if f.endswith(".png"):
                full_p = os.path.join(ios_icons, f)
                try:
                    with Image.open(full_p) as cur:
                        w, h = cur.size
                    master.resize((w, h), Image.Resampling.LANCZOS).save(full_p)
                    print(f"Updated iOS {f} ({w}x{h})")
                except Exception as e:
                    pass

if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    export_all_icons(root)
    print("ALL APP & FAVICON ASSETS SUCCESSFULLY GENERATED!")
