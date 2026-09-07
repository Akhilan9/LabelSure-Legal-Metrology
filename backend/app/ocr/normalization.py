import re
import unicodedata
from typing import Sequence

from app.models.ocr import OCRConfidenceTier
from app.ocr.schemas import BoundingBoxDict


def normalize_ocr_text(text: str) -> str:
    """Safely normalizes OCR recognized text without altering statutory values or spelling.

    Preserves numbers, currency symbols (₹, Rs.), units (g, ml, kg), and dates.
    """
    if not text:
        return ""

    # 1. Unicode NFKC normalization
    normalized = unicodedata.normalize("NFKC", text)

    # 2. Replace non-breaking spaces and exotic space characters with standard ASCII space
    normalized = re.sub(r"[   -     　]", " ", normalized)

    # 3. Collapse all whitespace, tabs, and newlines into single space
    normalized = re.sub(r"\s+", " ", normalized)

    # 4. Strip leading and trailing whitespace
    return normalized.strip()


def calculate_polygon_bounding_box(polygon: Sequence[Sequence[float | int]]) -> BoundingBoxDict:
    """Calculates axis-aligned bounding box from polygon coordinates."""
    if not polygon or len(polygon) < 2:
        return BoundingBoxDict(x_min=0.0, y_min=0.0, x_max=0.0, y_max=0.0, width=0.0, height=0.0)

    xs = [float(p[0]) for p in polygon]
    ys = [float(p[1]) for p in polygon]

    x_min = round(float(min(xs)), 2)
    y_min = round(float(min(ys)), 2)
    x_max = round(float(max(xs)), 2)
    y_max = round(float(max(ys)), 2)
    width = round(max(0.0, x_max - x_min), 2)
    height = round(max(0.0, y_max - y_min), 2)

    return BoundingBoxDict(
        x_min=x_min,
        y_min=y_min,
        x_max=x_max,
        y_max=y_max,
        width=width,
        height=height,
    )


def determine_confidence_tier(
    confidence: float,
    good_threshold: float = 0.85,
    review_threshold: float = 0.60,
) -> OCRConfidenceTier:
    """Maps continuous confidence score to explainable OCR quality tier."""
    if confidence >= good_threshold:
        return OCRConfidenceTier.GOOD
    elif confidence >= review_threshold:
        return OCRConfidenceTier.REVIEW
    else:
        return OCRConfidenceTier.LOW


def _extract_bbox_values(block: dict) -> tuple[float, float, float]:
    """Helper to extract (x_min, y_min, height) from a raw block dictionary."""
    bbox = block.get("bounding_box")
    if bbox is None:
        poly = block.get("polygon", [])
        bbox = calculate_polygon_bounding_box(poly)

    if isinstance(bbox, dict):
        x_min = float(bbox.get("x_min", bbox.get("x", 0.0)))
        y_min = float(bbox.get("y_min", bbox.get("y", 0.0)))
        height = float(bbox.get("height", 20.0))
    else:
        x_min = float(getattr(bbox, "x_min", getattr(bbox, "x", 0.0)))
        y_min = float(getattr(bbox, "y_min", getattr(bbox, "y", 0.0)))
        height = float(getattr(bbox, "height", 20.0))

    return x_min, y_min, max(5.0, height)


def sort_blocks_reading_order(blocks: list[dict]) -> list[dict]:
    """Sorts OCR blocks in standard document reading order (top-to-bottom, left-to-right).

    Groups nearby lines using a vertical proximity tolerance.
    """
    if not blocks:
        return []

    # Ensure all blocks have a valid bounding_box populated
    for block in blocks:
        if "bounding_box" not in block or block["bounding_box"] is None:
            poly = block.get("polygon", [])
            block["bounding_box"] = calculate_polygon_bounding_box(poly)

    # Sort primarily by y_min, secondary by x_min
    sorted_by_y = sorted(blocks, key=lambda b: (_extract_bbox_values(b)[1], _extract_bbox_values(b)[0]))

    # Line grouping with adaptive tolerance
    lines: list[list[dict]] = []
    current_line: list[dict] = []
    current_line_y = -1.0
    current_line_height = 20.0

    for block in sorted_by_y:
        x_min, y_min, height = _extract_bbox_values(block)

        if not current_line:
            current_line = [block]
            current_line_y = y_min
            current_line_height = height
        else:
            # Proximity tolerance: within 60% of the line height
            tolerance = current_line_height * 0.6
            if abs(y_min - current_line_y) <= tolerance:
                current_line.append(block)
                # Update moving average
                current_line_y = sum(_extract_bbox_values(b)[1] for b in current_line) / len(current_line)
                current_line_height = sum(_extract_bbox_values(b)[2] for b in current_line) / len(current_line)
            else:
                lines.append(sorted(current_line, key=lambda b: _extract_bbox_values(b)[0]))
                current_line = [block]
                current_line_y = y_min
                current_line_height = height

    if current_line:
        lines.append(sorted(current_line, key=lambda b: _extract_bbox_values(b)[0]))

    result: list[dict] = []
    reading_order = 0
    for line_idx, line in enumerate(lines):
        for block in line:
            block["reading_order"] = reading_order
            block["line_number"] = line_idx + 1
            reading_order += 1
            result.append(block)

    return result
