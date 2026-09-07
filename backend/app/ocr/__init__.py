from app.ocr.base import BaseOCRProvider
from app.ocr.normalization import (
    calculate_polygon_bounding_box,
    determine_confidence_tier,
    normalize_ocr_text,
    sort_blocks_reading_order,
)
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.providers.paddle import PaddleOCRProvider
from app.ocr.schemas import (
    BatchOCRResponse,
    BoundingBoxDict,
    InspectionOCRSummary,
    InspectionOCRSummaryPanel,
    OCRBlockResponse,
    OCRRunResponse,
    RawOCRBlockData,
    RawOCRRunResult,
)
from app.ocr.service import OCRService, get_ocr_provider, set_custom_ocr_provider, to_ocr_run_response

__all__ = [
    "BaseOCRProvider",
    "MockOCRProvider",
    "PaddleOCRProvider",
    "OCRService",
    "get_ocr_provider",
    "set_custom_ocr_provider",
    "to_ocr_run_response",
    "normalize_ocr_text",
    "calculate_polygon_bounding_box",
    "determine_confidence_tier",
    "sort_blocks_reading_order",
    "BoundingBoxDict",
    "RawOCRBlockData",
    "RawOCRRunResult",
    "OCRBlockResponse",
    "OCRRunResponse",
    "BatchOCRResponse",
    "InspectionOCRSummaryPanel",
    "InspectionOCRSummary",
]
