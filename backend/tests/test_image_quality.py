import io
import cv2
import numpy as np
from PIL import Image, ImageDraw
import pytest

from app.image_processing.preprocessing import ImagePreprocessor
from app.image_processing.quality import ImageQualityAnalyzer
from app.models.image_quality import QualityFlag, QualityStatus


def create_synthetic_image(
    width: int = 800,
    height: int = 800,
    bg_color: int = 180,
    add_text: bool = True,
    blur_kernel: int | None = None,
    glare_patch: bool = False,
) -> np.ndarray:
    """Helper to generate deterministic synthetic CV images for testing metrics."""
    img = np.full((height, width, 3), bg_color, dtype=np.uint8)

    if add_text:
        # Draw high-contrast header and text patterns simulating a real package label
        cv2.rectangle(img, (40, 40), (760, 120), (30, 30, 30), -1)
        cv2.putText(img, "PACKAGED COMMODITY", (60, 95), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 3)
        cv2.putText(img, "NET WEIGHT: 500g", (50, 200), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
        cv2.putText(img, "BATCH NO: B2026-X", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (20, 20, 20), 2)
        cv2.putText(img, "MRP: Rs. 149.00", (50, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (20, 20, 20), 3)
        cv2.rectangle(img, (40, 140), (760, 500), (10, 10, 10), 3)
        cv2.line(img, (50, 440), (750, 440), (0, 0, 0), 2)

    if glare_patch:
        # Add a large saturated near-white glare reflection patch
        cv2.rectangle(img, (200, 200), (600, 600), (255, 255, 255), -1)

    if blur_kernel:
        img = cv2.GaussianBlur(img, (blur_kernel, blur_kernel), 0)

    return img


def encode_image(img_arr: np.ndarray, ext: str = ".jpg") -> bytes:
    success, buffer = cv2.imencode(ext, img_arr)
    assert success
    return buffer.tobytes()


def test_analyzer_sharp_image_good_quality():
    analyzer = ImageQualityAnalyzer(min_width=600, min_height=600, blur_threshold=100.0)
    img = create_synthetic_image(width=800, height=800, bg_color=180, add_text=True)

    result = analyzer.analyze(img)
    assert result.width == 800
    assert result.height == 800
    assert result.channels == 3
    assert result.blur_score > 100.0
    assert result.brightness_score > 50.0 and result.brightness_score < 205.0
    assert result.contrast_score >= 30.0
    assert result.glare_score < 0.08
    assert len(result.flags) == 0
    assert result.status == QualityStatus.GOOD


def test_analyzer_blurry_image():
    analyzer = ImageQualityAnalyzer(blur_threshold=100.0)
    # Heavy Gaussian blur removes edge high-frequencies
    img = create_synthetic_image(width=800, height=800, bg_color=240, add_text=True, blur_kernel=31)

    result = analyzer.analyze(img)
    assert result.blur_score < 100.0
    assert QualityFlag.BLURRY.value in result.flags
    assert result.status in (QualityStatus.POOR, QualityStatus.UNREADABLE)


def test_analyzer_dark_image():
    analyzer = ImageQualityAnalyzer(brightness_low_threshold=50.0)
    img = create_synthetic_image(width=800, height=800, bg_color=25, add_text=True)

    result = analyzer.analyze(img)
    assert result.brightness_score < 50.0
    assert QualityFlag.TOO_DARK.value in result.flags


def test_analyzer_bright_and_glare_image():
    analyzer = ImageQualityAnalyzer(
        brightness_high_threshold=205.0,
        glare_pixel_threshold=250,
        glare_ratio_threshold=0.08,
    )
    img = create_synthetic_image(width=800, height=800, bg_color=240, add_text=True, glare_patch=True)

    result = analyzer.analyze(img)
    assert result.glare_score > 0.08
    assert QualityFlag.POSSIBLE_GLARE.value in result.flags


def test_analyzer_low_resolution_image():
    analyzer = ImageQualityAnalyzer(min_width=600, min_height=600)
    img = create_synthetic_image(width=400, height=400, bg_color=240, add_text=True)

    result = analyzer.analyze(img)
    assert result.width == 400
    assert result.height == 400
    assert QualityFlag.LOW_RESOLUTION.value in result.flags


def test_analyzer_invalid_empty_input():
    analyzer = ImageQualityAnalyzer()
    with pytest.raises(ValueError, match="Cannot analyze empty"):
        analyzer.analyze(np.array([]))


def test_preprocessor_decode_and_orient():
    preprocessor = ImagePreprocessor()

    img = create_synthetic_image(width=800, height=600)
    raw_bytes = encode_image(img, ".jpg")

    decoded = preprocessor.decode_and_orient(raw_bytes)
    assert decoded is not None
    assert decoded.shape[0] == 600
    assert decoded.shape[1] == 800
    assert decoded.shape[2] == 3


def test_preprocessor_pipeline_preserves_sharpness_and_encodes_png():
    preprocessor = ImagePreprocessor(max_dimension=1200)

    img = create_synthetic_image(width=1600, height=1200, bg_color=220, add_text=True)
    processed_cv, png_bytes = preprocessor.preprocess(img)

    assert processed_cv is not None
    # Max dimension normalized down to 1200
    assert max(processed_cv.shape[0], processed_cv.shape[1]) <= 1200
    assert len(png_bytes) > 0
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
