from pathlib import Path
from typing import Sequence

from app.models.ocr import OCRStatus
from app.ocr.base import BaseOCRProvider
from app.ocr.normalization import calculate_polygon_bounding_box, normalize_ocr_text
from app.ocr.schemas import RawOCRBlockData, RawOCRRunResult


class MockOCRProvider(BaseOCRProvider):
    """Deterministic Mock OCR provider for test suites and controlled simulation."""

    def __init__(
        self,
        default_blocks: Sequence[dict] | None = None,
        simulate_failure: bool = False,
        failure_error_code: str = "OCR_SIMULATED_FAILURE",
        failure_error_message: str = "Simulated OCR provider failure",
    ):
        self._default_blocks = default_blocks
        self._simulate_failure = simulate_failure
        self._failure_error_code = failure_error_code
        self._failure_error_message = failure_error_message

    @property
    def engine_name(self) -> str:
        return "MockOCR"

    @property
    def engine_version(self) -> str:
        return "1.0.0-test"

    def recognize_image_file(self, image_path: str | Path, language: str = "en") -> RawOCRRunResult:
        return self._process_mock_recognition(language=language)

    def recognize_image_bytes(self, image_bytes: bytes, language: str = "en") -> RawOCRRunResult:
        return self._process_mock_recognition(language=language)

    def _process_mock_recognition(self, language: str) -> RawOCRRunResult:
        if self._simulate_failure:
            return RawOCRRunResult(
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                language_config=language,
                status=OCRStatus.FAILED,
                average_confidence=None,
                blocks=[],
                error_code=self._failure_error_code,
                error_message_safe=self._failure_error_message,
            )

        blocks_data = self._default_blocks
        if blocks_data is None:
            # Default deterministic sample text blocks
            blocks_data = [
                {
                    "raw_text": "LABELSURE NUTRITION BARS",
                    "confidence": 0.98,
                    "polygon": [[20.0, 30.0], [380.0, 30.0], [380.0, 65.0], [20.0, 65.0]],
                },
                {
                    "raw_text": "Net Quantity: 250 g",
                    "confidence": 0.95,
                    "polygon": [[20.0, 80.0], [220.0, 80.0], [220.0, 110.0], [20.0, 110.0]],
                },
                {
                    "raw_text": "MRP: ₹ 95.00 (Incl. of all taxes)",
                    "confidence": 0.92,
                    "polygon": [[20.0, 125.0], [350.0, 125.0], [350.0, 155.0], [20.0, 155.0]],
                },
                {
                    "raw_text": "Mfg Date: 01/2026",
                    "confidence": 0.89,
                    "polygon": [[20.0, 170.0], [200.0, 170.0], [200.0, 195.0], [20.0, 195.0]],
                },
            ]

        parsed_blocks: list[RawOCRBlockData] = []
        confidences: list[float] = []

        for idx, item in enumerate(blocks_data):
            raw_text = item["raw_text"]
            norm_text = normalize_ocr_text(raw_text)
            conf = float(item["confidence"])
            poly = item["polygon"]
            bbox = calculate_polygon_bounding_box(poly)
            confidences.append(conf)

            parsed_blocks.append(
                RawOCRBlockData(
                    raw_text=raw_text,
                    normalized_text=norm_text,
                    confidence=conf,
                    polygon=poly,
                    bounding_box=bbox,
                    line_number=idx + 1,
                    reading_order=idx,
                )
            )

        avg_conf = round(sum(confidences) / len(confidences), 4) if confidences else None
        status = OCRStatus.SUCCESS if parsed_blocks else OCRStatus.PARTIAL

        return RawOCRRunResult(
            engine_name=self.engine_name,
            engine_version=self.engine_version,
            language_config=language,
            status=status,
            average_confidence=avg_conf,
            blocks=parsed_blocks,
            error_code=None,
            error_message_safe=None,
        )
