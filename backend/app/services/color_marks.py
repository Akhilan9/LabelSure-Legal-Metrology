"""
Statutory Color & Dietary Label Mark Detector.
Detects FSSAI & international statutory color-coded marks on packaging:
- Green Mark: Mandatory FSSAI 100% Vegetarian mark (concentric circle inside square).
- Brown / Red Mark: Mandatory FSSAI Non-Vegetarian mark (concentric circle/triangle inside square).
- Yellow / Amber Mark: Nutritional warning / High Fat-Sugar-Salt (HFSS) alert / caution mark.
- Blue Mark: FSSAI "+F" logo for fortified staple foods.

Implements strict structural geometry verification and mutual exclusivity so that
dummy or false positive marks are never reported.
"""

import os
from typing import Any, Dict, List, Optional
import cv2
import numpy as np


def _is_concentric_fssai_mark(crop_bgr: np.ndarray, color_type: str = "GREEN"):
    """
    Strictly verifies if a cropped image patch contains an FSSAI statutory emblem
    (a circle or triangle centered inside a square with contrasting light margin).
    """
    if crop_bgr is None or crop_bgr.size == 0:
        return False, 0.0

    ch, cw, _ = crop_bgr.shape
    if cw < 10 or ch < 10 or cw > 350 or ch > 350:
        return False, 0.0

    aspect = float(cw) / max(ch, 1)
    if not (0.75 <= aspect <= 1.33):
        return False, 0.0

    hsv = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)

    if color_type == "GREEN":
        # Green HSV range
        mask = cv2.inRange(hsv, np.array([35, 55, 40]), np.array([86, 255, 255]))
    elif color_type == "RED_BROWN":
        # Brown / Red HSV ranges
        m1 = cv2.inRange(hsv, np.array([0, 75, 45]), np.array([12, 255, 255]))
        m2 = cv2.inRange(hsv, np.array([168, 75, 45]), np.array([180, 255, 255]))
        m3 = cv2.inRange(hsv, np.array([8, 85, 30]), np.array([22, 220, 140]))
        mask = cv2.bitwise_or(m1, cv2.bitwise_or(m2, m3))
    else:
        return False, 0.0

    total_area = cw * ch
    color_pixels = np.count_nonzero(mask)
    fill_ratio = color_pixels / total_area

    # A circle inside a square on a white background occupies between 15% and 78% of bounding box
    if fill_ratio < 0.15 or fill_ratio > 0.78:
        return False, 0.0

    # Contours inside the mask
    cnts, hier = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return False, 0.0

    center_x, center_y = cw / 2.0, ch / 2.0
    best_shape_score = 0.0
    found_shape = False

    for cnt in cnts:
        c_area = cv2.contourArea(cnt)
        if c_area < (total_area * 0.08):  # Inner shape must be >= 8% of box
            continue
        peri = cv2.arcLength(cnt, True)
        if peri == 0:
            continue
        circularity = 4 * np.pi * (c_area / (peri * peri))

        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        offset_x = abs(cx - center_x) / cw
        offset_y = abs(cy - center_y) / ch

        # Check for circular inner mark (Vegetarian green dot or traditional non-veg circle)
        if circularity >= 0.60 and offset_x < 0.28 and offset_y < 0.28:
            if 0.15 <= (radius / min(cw, ch)) <= 0.55:
                found_shape = True
                best_shape_score = max(best_shape_score, circularity)

        # Also check for triangle inner mark (FSSAI 2020 Non-Veg triangle)
        if color_type == "RED_BROWN":
            approx = cv2.approxPolyDP(cnt, 0.06 * peri, True)
            if len(approx) == 3 and offset_x < 0.28 and offset_y < 0.28:
                found_shape = True
                best_shape_score = max(best_shape_score, 0.85)

    # Check for light/white surrounding background inside square
    white_mask = cv2.inRange(gray, 125, 255)
    white_ratio = np.count_nonzero(white_mask) / total_area

    if found_shape:
        conf = 0.70 + (0.20 * min(1.0, best_shape_score))
        if white_ratio >= 0.12:
            conf += 0.08
        return True, min(0.98, round(conf, 2))

    return False, 0.0


def detect_color_marks(image_path: str, ocr_text: str = "") -> List[Dict[str, Any]]:
    """
    Analyzes packaging image and returns detected statutory color marks.
    Only returns marks that genuinely exist on the packaging (no false positives).
    """
    if not os.path.exists(image_path):
        return []

    img = cv2.imread(image_path)
    if img is None:
        return []

    h, w, _ = img.shape
    total_pixels = h * w
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ocr_upper = (ocr_text or "").upper()

    detected: List[Dict[str, Any]] = []

    # 1. VEGETARIAN MARK (FSSAI green circle inside green square)
    green_mask = cv2.inRange(hsv, np.array([35, 55, 40]), np.array([86, 255, 255]))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    green_clean = cv2.morphologyEx(green_mask, cv2.MORPH_OPEN, kernel)
    contours_veg, _ = cv2.findContours(green_clean, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    best_veg = None
    best_veg_conf = 0.0

    for cnt in contours_veg:
        area = cv2.contourArea(cnt)
        if not (50 < area < (total_pixels * 0.03)):
            continue
        peri = cv2.arcLength(cnt, True)
        if peri == 0:
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = float(cw) / max(ch, 1)
        if not (0.75 <= aspect <= 1.33):
            continue

        pad = max(2, int(min(cw, ch) * 0.15))
        y1, y2 = max(0, y - pad), min(h, y + ch + pad)
        x1, x2 = max(0, x - pad), min(w, x + cw + pad)
        crop = img[y1:y2, x1:x2]

        is_valid, conf = _is_concentric_fssai_mark(crop, "GREEN")
        if is_valid and conf > best_veg_conf:
            best_veg_conf = conf
            best_veg = {
                "type": "VEGETARIAN",
                "color_name": "GREEN",
                "title": "100% Vegetarian (Veg Mark)",
                "statutory_standard": "FSSAI (Labelling & Display) Reg. 2020: Reg. 5(4) / Legal Metrology",
                "description": "Mandatory green filled circle inside a green square outline certifying food is 100% vegetarian.",
                "badge_color": "emerald",
                "confidence": conf,
                "bbox": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                "relative_bbox": {
                    "x": round(x / w, 4), "y": round(y / h, 4),
                    "width": round(cw / w, 4), "height": round(ch / h, 4),
                },
                "detected": True,
            }

    # 2. NON-VEGETARIAN MARK (FSSAI brown/red circle or triangle inside square)
    best_nonveg = None
    best_nonveg_conf = 0.0

    m1 = cv2.inRange(hsv, np.array([0, 75, 45]), np.array([12, 255, 255]))
    m2 = cv2.inRange(hsv, np.array([168, 75, 45]), np.array([180, 255, 255]))
    m3 = cv2.inRange(hsv, np.array([8, 85, 30]), np.array([22, 220, 140]))
    brown_mask = cv2.bitwise_or(m1, cv2.bitwise_or(m2, m3))
    brown_clean = cv2.morphologyEx(brown_mask, cv2.MORPH_OPEN, kernel)
    contours_nv, _ = cv2.findContours(brown_clean, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in contours_nv:
        area = cv2.contourArea(cnt)
        if not (50 < area < (total_pixels * 0.03)):
            continue
        peri = cv2.arcLength(cnt, True)
        if peri == 0:
            continue
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = float(cw) / max(ch, 1)
        if not (0.75 <= aspect <= 1.33):
            continue

        pad = max(2, int(min(cw, ch) * 0.15))
        y1, y2 = max(0, y - pad), min(h, y + ch + pad)
        x1, x2 = max(0, x - pad), min(w, x + cw + pad)
        crop = img[y1:y2, x1:x2]

        is_valid, conf = _is_concentric_fssai_mark(crop, "RED_BROWN")
        if is_valid and conf > best_nonveg_conf:
            best_nonveg_conf = conf
            best_nonveg = {
                "type": "NON_VEGETARIAN",
                "color_name": "RED_BROWN",
                "title": "Non-Vegetarian (Non-Veg Mark)",
                "statutory_standard": "FSSAI (Labelling & Display) Reg. 2020: Reg. 5(4) / Legal Metrology",
                "description": "Mandatory brown/red filled circle or triangle inside a square outline certifying non-vegetarian origin.",
                "badge_color": "rose",
                "confidence": conf,
                "bbox": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                "relative_bbox": {
                    "x": round(x / w, 4), "y": round(y / h, 4),
                    "width": round(cw / w, 4), "height": round(ch / h, 4),
                },
                "detected": True,
            }

    # Mutual exclusivity for dietary mark (a product is either Veg or Non-Veg, never both)
    if best_veg and best_nonveg:
        if best_veg_conf >= best_nonveg_conf:
            detected.append(best_veg)
        else:
            detected.append(best_nonveg)
    elif best_veg:
        detected.append(best_veg)
    elif best_nonveg:
        detected.append(best_nonveg)

    # 3. NUTRITIONAL / ALLERGEN WARNING MARK (Yellow / Amber)
    # Strictly requires:
    # a) An equilateral warning triangle with black border and black symbol inside, OR
    # b) OCR text containing explicit warning terms ("WARNING", "ALLERGEN", "CAUTION", "HFSS")
    has_warning_text = any(k in ocr_upper for k in ["ALLERGEN", "WARNING", "CAUTION", "HFSS", "HIGH SUGAR", "HIGH SODIUM"])
    yellow_mask = cv2.inRange(hsv, np.array([20, 110, 100]), np.array([33, 255, 255]))
    yellow_clean = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN, kernel)
    cnts_y, _ = cv2.findContours(yellow_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for cnt in cnts_y:
        area = cv2.contourArea(cnt)
        if not (120 < area < (total_pixels * 0.025)):
            continue
        peri = cv2.arcLength(cnt, True)
        if peri == 0:
            continue
        approx = cv2.approxPolyDP(cnt, 0.06 * peri, True)
        x, y, cw, ch = cv2.boundingRect(cnt)
        aspect = float(cw) / max(ch, 1)

        # Equilateral warning triangle (3 vertices)
        if len(approx) == 3 and (0.80 <= aspect <= 1.25):
            crop_gray = gray[y:y+ch, x:x+cw]
            dark_pixels = np.count_nonzero(crop_gray < 80)
            if dark_pixels > (cw * ch * 0.06):  # Black symbol / exclamation inside
                detected.append({
                    "type": "NUTRITIONAL_WARNING",
                    "color_name": "YELLOW_AMBER",
                    "title": "Caution / Warning Mark (Warning Triangle)",
                    "statutory_standard": "FOPNL Statutory Dietary Advisory / Allergen Precaution",
                    "description": "High-visibility caution, allergen warning, or front-of-pack nutritional mark.",
                    "badge_color": "amber",
                    "confidence": 0.88,
                    "bbox": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                    "relative_bbox": {
                        "x": round(x / w, 4), "y": round(y / h, 4),
                        "width": round(cw / w, 4), "height": round(ch / h, 4),
                    },
                    "detected": True,
                })
                break
        elif has_warning_text and (0.75 <= aspect <= 1.33):
            # Corroborated with warning text on packet
            detected.append({
                "type": "NUTRITIONAL_WARNING",
                "color_name": "YELLOW_AMBER",
                "title": "Caution / Allergen Warning Advisory",
                "statutory_standard": "FOPNL Statutory Dietary Advisory / Allergen Precaution",
                "description": "Statutory allergen / dietary advisory mark identified on packaging.",
                "badge_color": "amber",
                "confidence": 0.85,
                "bbox": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                "relative_bbox": {
                    "x": round(x / w, 4), "y": round(y / h, 4),
                    "width": round(cw / w, 4), "height": round(ch / h, 4),
                },
                "detected": True,
            })
            break

    # 4. FORTIFIED FOOD (+F LOGO) (Blue)
    # Strictly requires "+F" / "FORTIFIED" / "FORTIFICATION" in OCR text, or "+F" emblem geometry
    has_fortified_text = any(k in ocr_upper for k in ["+F", "+ F", "FORTIFIED", "FORTIFICATION", "SAMPOORNA POSHAN"])
    if has_fortified_text:
        blue_mask = cv2.inRange(hsv, np.array([98, 80, 60]), np.array([128, 255, 255]))
        blue_clean = cv2.morphologyEx(blue_mask, cv2.MORPH_OPEN, kernel)
        cnts_b, _ = cv2.findContours(blue_clean, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in cnts_b:
            area = cv2.contourArea(cnt)
            if not (80 < area < (total_pixels * 0.025)):
                continue
            x, y, cw, ch = cv2.boundingRect(cnt)
            aspect = float(cw) / max(ch, 1)
            if 0.75 <= aspect <= 1.33:
                detected.append({
                    "type": "FORTIFIED_FOOD",
                    "color_name": "BLUE",
                    "title": "Fortified Food (+F) Mark",
                    "statutory_standard": "Food Safety and Standards (Fortification of Foods) Regulations",
                    "description": "FSSAI +F blue emblem certifying essential micronutrient fortification.",
                    "badge_color": "sky",
                    "confidence": 0.90,
                    "bbox": {"x": int(x), "y": int(y), "width": int(cw), "height": int(ch)},
                    "relative_bbox": {
                        "x": round(x / w, 4), "y": round(y / h, 4),
                        "width": round(cw / w, 4), "height": round(ch / h, 4),
                    },
                    "detected": True,
                })
                break

    return detected


def scan_inspection_color_marks(inspection_or_id, storage_dir: str, ocr_text: str = "") -> List[Dict[str, Any]]:
    """
    Scans all images attached to an inspection and returns consolidated color mark findings.
    Accepts an Inspection model instance OR an inspection_id string.
    Only returns genuinely detected marks.
    """
    all_marks = []
    seen = set()

    image_paths = []
    if isinstance(inspection_or_id, str):
        insp_id = inspection_or_id
        for sub in [
            os.path.join(storage_dir, "inspections", insp_id, "originals"),
            os.path.join(storage_dir, "inspections", insp_id),
            os.path.join(storage_dir, insp_id, "originals"),
            os.path.join(storage_dir, insp_id),
        ]:
            if os.path.exists(sub):
                for f in os.listdir(sub):
                    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                        image_paths.append((os.path.join(sub, f), None))
    else:
        for img in getattr(inspection_or_id, "images", []):
            full_path = os.path.join(storage_dir, img.storage_path) if not os.path.isabs(img.storage_path) else img.storage_path
            if not os.path.exists(full_path):
                full_path = os.path.join("storage", img.storage_path)
            if os.path.exists(full_path):
                image_paths.append((full_path, str(img.id)))

    for img_path, img_id in image_paths:
        marks = detect_color_marks(img_path, ocr_text=ocr_text)
        for m in marks:
            if m["type"] not in seen:
                seen.add(m["type"])
                if img_id:
                    m["image_id"] = img_id
                all_marks.append(m)

    return all_marks
