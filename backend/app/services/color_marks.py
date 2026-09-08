"""
Statutory Color & Dietary Label Mark Detector.
Detects FSSAI & international statutory color-coded marks on packaging:
- Green Mark: Mandatory FSSAI 100% Vegetarian mark (circle inside square).
- Brown / Red Mark: Mandatory FSSAI Non-Vegetarian mark (circle/triangle inside square).
- Yellow / Amber Mark: Nutritional warning / High Fat-Sugar-Salt (HFSS) alert / caution mark.
- Blue Mark: FSSAI "+F" logo for fortified staple foods.
"""

import os
from typing import Any, Dict, List, Optional
import cv2
import numpy as np

# Color definitions in HSV
COLOR_PROFILES = [
    {
        "type": "VEGETARIAN",
        "color_name": "GREEN",
        "title": "100% Vegetarian (Veg Mark)",
        "statutory_standard": "FSSAI (Labelling & Display) Reg. 2020: Reg. 5(4) / Legal Metrology",
        "description": "Mandatory green filled circle inside a green square outline certifying food is 100% vegetarian.",
        "badge_color": "emerald",
        "ranges": [
            (np.array([35, 60, 45]), np.array([86, 255, 255]))
        ],
    },
    {
        "type": "NON_VEGETARIAN",
        "color_name": "RED_BROWN",
        "title": "Non-Vegetarian (Non-Veg Mark)",
        "statutory_standard": "FSSAI (Labelling & Display) Reg. 2020: Reg. 5(4) / Legal Metrology",
        "description": "Mandatory brown/red filled circle or triangle inside a square outline certifying non-vegetarian origin.",
        "badge_color": "rose",
        "ranges": [
            (np.array([0, 80, 50]), np.array([12, 255, 255])),
            (np.array([168, 80, 50]), np.array([180, 255, 255])),
            (np.array([8, 90, 30]), np.array([22, 220, 140]))  # Brown
        ],
    },
    {
        "type": "NUTRITIONAL_WARNING",
        "color_name": "YELLOW_AMBER",
        "title": "Caution / Allergen / Warning Mark",
        "statutory_standard": "FOPNL Statutory Dietary Advisory / Allergen Precaution",
        "description": "High-visibility caution, allergen warning, or front-of-pack nutritional mark.",
        "badge_color": "amber",
        "ranges": [
            (np.array([20, 100, 90]), np.array([33, 255, 255]))
        ],
    },
    {
        "type": "FORTIFIED_FOOD",
        "color_name": "BLUE",
        "title": "Fortified Food (+F) Mark",
        "statutory_standard": "Food Safety and Standards (Fortification of Foods) Regulations",
        "description": "FSSAI +F blue emblem certifying essential micronutrient fortification.",
        "badge_color": "sky",
        "ranges": [
            (np.array([98, 80, 60]), np.array([128, 255, 255]))
        ],
    },
]


def detect_color_marks(image_path: str) -> List[Dict[str, Any]]:
    """
    Analyzes packaging image and returns detected statutory color marks and symbols.
    """
    if not os.path.exists(image_path):
        return []

    img = cv2.imread(image_path)
    if img is None:
        return []

    h, w, _ = img.shape
    total_pixels = h * w
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    detected: List[Dict[str, Any]] = []
    seen_types: set = set()

    for profile in COLOR_PROFILES:
        mask = np.zeros((h, w), dtype=np.uint8)
        for lower, upper in profile["ranges"]:
            mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))

        # Morphological clean up
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)

        contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []

        for i, cnt in enumerate(contours):
            area = cv2.contourArea(cnt)
            # Filter noise and huge backgrounds (marks are typically 0.02% to 2.5% of label)
            if 70 < area < (total_pixels * 0.03):
                peri = cv2.arcLength(cnt, True)
                if peri == 0:
                    continue
                approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                x, y, cw, ch = cv2.boundingRect(cnt)
                aspect_ratio = float(cw) / max(ch, 1)

                # Marks are symmetrical (aspect ratio 0.75 to 1.33)
                if 0.75 <= aspect_ratio <= 1.33:
                    extent = area / (cw * ch)
                    circularity = 4 * np.pi * (area / (peri * peri))

                    # High quality mark: circle/square (extent 0.65 to 1.0)
                    if 0.55 <= extent <= 1.0:
                        has_child = hierarchy[0][i][2] != -1 if hierarchy is not None and len(hierarchy) > 0 else False
                        candidates.append({
                            "area": area,
                            "x": x,
                            "y": y,
                            "width": cw,
                            "height": ch,
                            "extent": extent,
                            "circularity": circularity,
                            "has_child": has_child,
                        })

        if candidates:
            # Sort candidates by area and circularity/fill density
            candidates.sort(key=lambda c: (c["has_child"], c["circularity"], c["area"]), reverse=True)
            best = candidates[0]

            # Confidence based on geometry
            confidence = 0.75
            if best["has_child"]:
                confidence += 0.15  # Circle inside square outline!
            if 0.65 <= best["circularity"] <= 1.2:
                confidence += 0.08
            confidence = min(0.99, max(0.70, confidence))

            mark_type = profile["type"]
            if mark_type not in seen_types:
                seen_types.add(mark_type)
                detected.append({
                    "type": mark_type,
                    "color_name": profile["color_name"],
                    "title": profile["title"],
                    "statutory_standard": profile["statutory_standard"],
                    "description": profile["description"],
                    "badge_color": profile["badge_color"],
                    "confidence": round(confidence, 2),
                    "bbox": {
                        "x": int(best["x"]),
                        "y": int(best["y"]),
                        "width": int(best["width"]),
                        "height": int(best["height"]),
                    },
                    "relative_bbox": {
                        "x": round(best["x"] / w, 4),
                        "y": round(best["y"] / h, 4),
                        "width": round(best["width"] / w, 4),
                        "height": round(best["height"] / h, 4),
                    },
                    "detected": True,
                })

    return detected


def scan_inspection_color_marks(inspection, storage_dir: str) -> List[Dict[str, Any]]:
    """
    Scans all images attached to an inspection and returns consolidated color mark findings.
    """
    all_marks = []
    seen = set()

    for img in getattr(inspection, "images", []):
        full_path = os.path.join(storage_dir, img.storage_path) if not os.path.isabs(img.storage_path) else img.storage_path
        if not os.path.exists(full_path):
            full_path = os.path.join("storage", img.storage_path)

        if os.path.exists(full_path):
            marks = detect_color_marks(full_path)
            for m in marks:
                if m["type"] not in seen:
                    seen.add(m["type"])
                    m["image_id"] = str(img.id)
                    all_marks.append(m)

    return all_marks
