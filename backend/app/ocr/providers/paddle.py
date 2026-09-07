import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.models.ocr import OCRStatus
from app.ocr.base import BaseOCRProvider
from app.ocr.normalization import calculate_polygon_bounding_box, normalize_ocr_text, sort_blocks_reading_order
from app.ocr.schemas import RawOCRBlockData, RawOCRRunResult

logger = logging.getLogger("labelsure.ocr.paddle")


class PaddleOCRProvider(BaseOCRProvider):
    """Real PaddleOCR provider utilizing lightweight CPU inference for package evidence text."""

    def __init__(
        self,
        use_gpu: bool = False,
        enable_mkldnn: bool = False,
        default_language: str = "en",
    ):
        self._use_gpu = use_gpu
        self._enable_mkldnn = enable_mkldnn
        self._default_language = default_language
        self._ocr_instances: dict[str, Any] = {}
        self._engine_version_str = "3.7.0"

    @property
    def engine_name(self) -> str:
        return "PaddleOCR"

    @property
    def engine_version(self) -> str:
        return self._engine_version_str

    def _get_ocr_engine(self, language: str) -> Any:
        """Lazily instantiates and caches the PaddleOCR engine for the given language."""
        if language in self._ocr_instances:
            return self._ocr_instances[language]

        try:
            import os
            os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
            from paddleocr import PaddleOCR

            # Initialize lightweight, stable CPU config
            engine = PaddleOCR(
                lang=language,
                use_textline_orientation=False,
                use_doc_orientation_classify=False,
                use_doc_unwarping=False,
                enable_mkldnn=self._enable_mkldnn,
            )
            self._ocr_instances[language] = engine
            return engine
        except Exception as exc:
            logger.error("Failed to initialize PaddleOCR engine for language '%s': %s", language, exc)
            raise RuntimeError(f"Could not initialize PaddleOCR engine: {exc}") from exc

    def recognize_image_file(self, image_path: str | Path, language: str = "en") -> RawOCRRunResult:
        """Runs PaddleOCR on an image file on disk."""
        path_obj = Path(image_path)
        if not path_obj.exists() or not path_obj.is_file():
            return RawOCRRunResult(
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                language_config=language,
                status=OCRStatus.FAILED,
                average_confidence=None,
                blocks=[],
                error_code="IMAGE_FILE_NOT_FOUND",
                error_message_safe="Evidence image artifact could not be found on storage.",
            )

        try:
            # Read via OpenCV
            img_bytes = path_obj.read_bytes()
            return self.recognize_image_bytes(img_bytes, language=language)
        except Exception as exc:
            logger.exception("Unexpected error reading image file for OCR: %s", exc)
            return RawOCRRunResult(
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                language_config=language,
                status=OCRStatus.FAILED,
                average_confidence=None,
                blocks=[],
                error_code="OCR_READ_ERROR",
                error_message_safe="Failed to read image artifact for OCR processing.",
            )

    def recognize_image_bytes(self, image_bytes: bytes, language: str = "en") -> RawOCRRunResult:
        """Runs PaddleOCR on image bytes in memory."""
        if not image_bytes or len(image_bytes) == 0:
            return RawOCRRunResult(
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                language_config=language,
                status=OCRStatus.FAILED,
                average_confidence=None,
                blocks=[],
                error_code="EMPTY_IMAGE_BYTES",
                error_message_safe="Image evidence bytes are empty.",
            )

        try:
            np_arr = np.frombuffer(image_bytes, np.uint8)
            image_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            if image_bgr is None:
                return RawOCRRunResult(
                    engine_name=self.engine_name,
                    engine_version=self.engine_version,
                    language_config=language,
                    status=OCRStatus.FAILED,
                    average_confidence=None,
                    blocks=[],
                    error_code="INVALID_IMAGE_DECODE",
                    error_message_safe="Unable to decode image evidence into valid pixel frame.",
                )

            engine = self._get_ocr_engine(language)
            predictions = engine.predict(image_bgr)

            raw_block_dicts: list[dict] = []
            confidences: list[float] = []

            for pred in predictions:
                if not hasattr(pred, "get"):
                    continue

                texts = pred.get("rec_texts", [])
                scores = pred.get("rec_scores", [])
                polys = pred.get("rec_polys", pred.get("dt_polys", []))

                for text_str, score_val, poly_arr in zip(texts, scores, polys):
                    if not text_str or not str(text_str).strip():
                        continue

                    raw_text = str(text_str)
                    norm_text = normalize_ocr_text(raw_text)
                    conf = round(float(score_val), 4)
                    poly_list = poly_arr.tolist() if hasattr(poly_arr, "tolist") else [list(p) for p in poly_arr]
                    bbox = calculate_polygon_bounding_box(poly_list)

                    confidences.append(conf)
                    raw_block_dicts.append({
                        "raw_text": raw_text,
                        "normalized_text": norm_text,
                        "confidence": conf,
                        "polygon": poly_list,
                        "bounding_box": bbox,
                    })

            # Sort reading order
            sorted_blocks = sort_blocks_reading_order(raw_block_dicts)

            parsed_blocks: list[RawOCRBlockData] = [
                RawOCRBlockData(
                    raw_text=b["raw_text"],
                    normalized_text=b["normalized_text"],
                    confidence=b["confidence"],
                    polygon=b["polygon"],
                    bounding_box=b["bounding_box"],
                    line_number=b.get("line_number"),
                    reading_order=b.get("reading_order"),
                )
                for b in sorted_blocks
            ]

            avg_confidence = round(sum(confidences) / len(confidences), 4) if confidences else None
            status = OCRStatus.SUCCESS if parsed_blocks else OCRStatus.PARTIAL

            return RawOCRRunResult(
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                language_config=language,
                status=status,
                average_confidence=avg_confidence,
                blocks=parsed_blocks,
                error_code=None,
                error_message_safe=None,
            )

        except Exception as exc:
            logger.exception("OCR recognition failure in PaddleOCR: %s", exc)
            return RawOCRRunResult(
                engine_name=self.engine_name,
                engine_version=self.engine_version,
                language_config=language,
                status=OCRStatus.FAILED,
                average_confidence=None,
                blocks=[],
                error_code="PADDLE_OCR_INFERENCE_ERROR",
                error_message_safe="An error occurred during OCR text inference on the evidence frame.",
            )
