import pytest

from app.models.ocr import OCRConfidenceTier, OCRStatus
from app.ocr.normalization import (
    calculate_polygon_bounding_box,
    determine_confidence_tier,
    normalize_ocr_text,
    sort_blocks_reading_order,
)
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.providers.paddle import PaddleOCRProvider


def test_normalize_ocr_text():
    # 1. Unicode normalization (NFKC)
    assert normalize_ocr_text("Net  Quantity:   500 g") == "Net Quantity: 500 g"

    # 2. Tabs and newlines collapsing
    assert normalize_ocr_text("MRP:  \t ₹ 95.00 \n (Incl. of taxes)") == "MRP: ₹ 95.00 (Incl. of taxes)"

    # 3. Leading and trailing whitespace stripping
    assert normalize_ocr_text("   Manufactured by Apex Foods Ltd   ") == "Manufactured by Apex Foods Ltd"

    # 4. Preserves legal metrology numbers and symbols
    assert normalize_ocr_text("Batch No: B-2026/09, Exp: 12/2027") == "Batch No: B-2026/09, Exp: 12/2027"
    assert normalize_ocr_text("Net Wt: 1.5 kg / 1500 g") == "Net Wt: 1.5 kg / 1500 g"


def test_calculate_polygon_bounding_box():
    # 4-point rectangle polygon
    poly = [[20.0, 30.0], [120.0, 30.0], [120.0, 70.0], [20.0, 70.0]]
    bbox = calculate_polygon_bounding_box(poly)

    assert bbox.x_min == 20.0
    assert bbox.y_min == 30.0
    assert bbox.x_max == 120.0
    assert bbox.y_max == 70.0
    assert bbox.width == 100.0
    assert bbox.height == 40.0


def test_calculate_polygon_bounding_box_empty():
    bbox = calculate_polygon_bounding_box([])
    assert bbox.x_min == 0.0
    assert bbox.y_min == 0.0
    assert bbox.width == 0.0
    assert bbox.height == 0.0


def test_determine_confidence_tier():
    # Default thresholds: Good >= 0.85, Review >= 0.60
    assert determine_confidence_tier(0.95, 0.85, 0.60) == OCRConfidenceTier.GOOD
    assert determine_confidence_tier(0.85, 0.85, 0.60) == OCRConfidenceTier.GOOD
    assert determine_confidence_tier(0.84, 0.85, 0.60) == OCRConfidenceTier.REVIEW
    assert determine_confidence_tier(0.60, 0.85, 0.60) == OCRConfidenceTier.REVIEW
    assert determine_confidence_tier(0.59, 0.85, 0.60) == OCRConfidenceTier.LOW
    assert determine_confidence_tier(0.10, 0.85, 0.60) == OCRConfidenceTier.LOW


def test_sort_blocks_reading_order():
    # Blocks scrambled in order: line 2 right, line 1 left, line 2 left, line 1 right
    blocks = [
        {"raw_text": "L2_Right", "polygon": [[200.0, 100.0], [350.0, 100.0], [350.0, 130.0], [200.0, 130.0]]},
        {"raw_text": "L1_Left", "polygon": [[20.0, 30.0], [150.0, 30.0], [150.0, 60.0], [20.0, 60.0]]},
        {"raw_text": "L2_Left", "polygon": [[20.0, 100.0], [150.0, 100.0], [150.0, 130.0], [20.0, 130.0]]},
        {"raw_text": "L1_Right", "polygon": [[200.0, 30.0], [350.0, 30.0], [350.0, 60.0], [200.0, 60.0]]},
    ]

    sorted_blocks = sort_blocks_reading_order(blocks)
    texts = [b["raw_text"] for b in sorted_blocks]

    # Reading order should be Line 1 left -> Line 1 right -> Line 2 left -> Line 2 right
    assert texts == ["L1_Left", "L1_Right", "L2_Left", "L2_Right"]
    assert [b["reading_order"] for b in sorted_blocks] == [0, 1, 2, 3]
    assert [b["line_number"] for b in sorted_blocks] == [1, 1, 2, 2]


def test_mock_ocr_provider_success():
    provider = MockOCRProvider()
    assert provider.engine_name == "MockOCR"
    assert provider.engine_version == "1.0.0-test"

    result = provider.recognize_image_bytes(b"dummy_bytes", language="en")
    assert result.status == OCRStatus.SUCCESS
    assert result.engine_name == "MockOCR"
    assert len(result.blocks) >= 4
    assert result.average_confidence is not None
    assert result.average_confidence >= 0.85
    assert result.error_code is None

    first_block = result.blocks[0]
    assert "LABELSURE" in first_block.raw_text
    assert first_block.bounding_box is not None
    assert first_block.reading_order == 0


def test_mock_ocr_provider_simulated_failure():
    provider = MockOCRProvider(
        simulate_failure=True,
        failure_error_code="TEST_FAILURE",
        failure_error_message="Simulated OCR crash",
    )
    result = provider.recognize_image_bytes(b"dummy_bytes", language="en")

    assert result.status == OCRStatus.FAILED
    assert result.error_code == "TEST_FAILURE"
    assert result.error_message_safe == "Simulated OCR crash"
    assert len(result.blocks) == 0
    assert result.average_confidence is None


def test_paddle_ocr_provider_properties():
    provider = PaddleOCRProvider(use_gpu=False, enable_mkldnn=False, default_language="en")
    assert provider.engine_name == "PaddleOCR"
    assert provider.engine_version == "3.7.0"

    # Empty bytes test
    empty_result = provider.recognize_image_bytes(b"")
    assert empty_result.status == OCRStatus.FAILED
    assert empty_result.error_code == "EMPTY_IMAGE_BYTES"

    # Invalid image bytes test
    invalid_result = provider.recognize_image_bytes(b"not_an_image")
    assert invalid_result.status == OCRStatus.FAILED
    assert invalid_result.error_code == "INVALID_IMAGE_DECODE"
