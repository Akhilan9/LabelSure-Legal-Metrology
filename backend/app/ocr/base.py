from abc import ABC, abstractmethod
from pathlib import Path

from app.ocr.schemas import RawOCRRunResult


class BaseOCRProvider(ABC):
    """Abstract Base Class for OCR providers (PaddleOCR, Mock/Fake)."""

    @property
    @abstractmethod
    def engine_name(self) -> str:
        """Returns the human-readable identifier of the OCR engine."""
        pass

    @property
    @abstractmethod
    def engine_version(self) -> str:
        """Returns the semantic version string of the engine."""
        pass

    @abstractmethod
    def recognize_image_file(self, image_path: str | Path, language: str = "en") -> RawOCRRunResult:
        """Runs OCR recognition on an image file stored on disk.

        Args:
            image_path: Absolute or safe resolved path to image file.
            language: Target OCR language configuration code.

        Returns:
            RawOCRRunResult containing status, confidence, and polygon text blocks.
        """
        pass

    @abstractmethod
    def recognize_image_bytes(self, image_bytes: bytes, language: str = "en") -> RawOCRRunResult:
        """Runs OCR recognition on raw image bytes.

        Args:
            image_bytes: Raw bytes of the image (PNG/JPEG).
            language: Target OCR language configuration code.

        Returns:
            RawOCRRunResult containing status, confidence, and polygon text blocks.
        """
        pass
