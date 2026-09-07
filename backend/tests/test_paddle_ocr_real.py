import cv2
import numpy as np
import pytest

from app.models.ocr import OCRStatus
from app.ocr.providers.paddle import PaddleOCRProvider


def test_paddle_ocr_real_cpu_inference():
    """Live smoke test executing real PaddleOCR inference on CPU for synthetic package evidence."""
    pytest.importorskip("paddleocr")
    # 1. Generate clean synthetic commodity label
    img = np.full((300, 800, 3), 255, dtype=np.uint8)
    cv2.rectangle(img, (20, 20), (780, 80), (10, 50, 10), -1)
    cv2.putText(img, "LABELSURE NUTRITION", (40, 62), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    cv2.putText(img, "Net Quantity: 500 g", (40, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    cv2.putText(img, "MRP: Rs. 150.00", (40, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    success, buffer = cv2.imencode(".jpg", img)
    assert success
    img_bytes = buffer.tobytes()

    # 2. Run real PaddleOCRProvider on CPU
    provider = PaddleOCRProvider(use_gpu=False, enable_mkldnn=False, default_language="en")
    result = provider.recognize_image_bytes(img_bytes, language="en")

    assert result.status == OCRStatus.SUCCESS
    assert result.engine_name == "PaddleOCR"
    assert result.engine_version == "3.7.0"
    assert len(result.blocks) >= 2
    assert result.average_confidence is not None
    assert result.average_confidence > 0.70

    recognized_texts = [b.raw_text.upper() for b in result.blocks]
    combined_text = " ".join(recognized_texts)

    # Verify key tokens extracted by real deep learning OCR model
    assert any("QUANTITY" in t or "500" in t for t in recognized_texts) or "500" in combined_text
    assert any("MRP" in t or "150" in t for t in recognized_texts) or "150" in combined_text
