from dataclasses import dataclass, field
import cv2
import numpy as np

from app.models.image_quality import QualityFlag, QualityStatus


@dataclass
class QualityAssessmentResult:
    width: int
    height: int
    channels: int
    blur_score: float
    brightness_score: float
    contrast_score: float
    glare_score: float
    flags: list[str] = field(default_factory=list)
    status: QualityStatus = QualityStatus.GOOD


class ImageQualityAnalyzer:
    """
    Computes explainable image quality metrics on package evidence images.

    Metrics:
    - Focus/Blur: Variance of Laplacian. Higher value = sharper edges; lower value = blurry.
    - Brightness: Mean of grayscale luminance intensities [0.0 - 255.0].
    - Contrast: Standard deviation of grayscale pixel intensities. Higher value = dynamic range.
    - Glare / Overexposure: Ratio of near-white pixels (intensity >= glare_pixel_threshold) [0.0 - 1.0].
    - Resolution: Dimensions checked against minimum operational thresholds.
    """

    def __init__(
        self,
        min_width: int = 600,
        min_height: int = 600,
        blur_threshold: float = 100.0,
        brightness_low_threshold: float = 50.0,
        brightness_high_threshold: float = 205.0,
        contrast_threshold: float = 30.0,
        glare_pixel_threshold: int = 250,
        glare_ratio_threshold: float = 0.08,
    ):
        self.min_width = min_width
        self.min_height = min_height
        self.blur_threshold = blur_threshold
        self.brightness_low_threshold = brightness_low_threshold
        self.brightness_high_threshold = brightness_high_threshold
        self.contrast_threshold = contrast_threshold
        self.glare_pixel_threshold = glare_pixel_threshold
        self.glare_ratio_threshold = glare_ratio_threshold

    def analyze(self, image: np.ndarray) -> QualityAssessmentResult:
        if image is None or image.size == 0:
            raise ValueError("Cannot analyze empty or invalid image array")

        height, width = image.shape[:2]
        channels = image.shape[2] if len(image.shape) > 2 else 1

        if len(image.shape) == 3 and image.shape[2] >= 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        elif len(image.shape) == 2:
            gray = image
        else:
            gray = image[:, :, 0]

        # 1. Blur calculation (Variance of Laplacian)
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = round(float(laplacian.var()), 2)

        # 2. Brightness (Mean grayscale intensity)
        brightness_score = round(float(np.mean(gray)), 2)

        # 3. Contrast (Standard deviation of grayscale intensity)
        contrast_score = round(float(np.std(gray)), 2)

        # 4. Glare / Overexposed pixel ratio
        glare_pixels = np.sum(gray >= self.glare_pixel_threshold)
        total_pixels = max(1, width * height)
        glare_score = round(float(glare_pixels / total_pixels), 4)

        # 5. Evaluate flags
        flags: list[str] = []

        if blur_score < self.blur_threshold:
            flags.append(QualityFlag.BLURRY.value)

        if brightness_score < self.brightness_low_threshold:
            flags.append(QualityFlag.TOO_DARK.value)
        elif brightness_score > self.brightness_high_threshold:
            flags.append(QualityFlag.TOO_BRIGHT.value)

        if contrast_score < self.contrast_threshold:
            flags.append(QualityFlag.LOW_CONTRAST.value)

        if glare_score > self.glare_ratio_threshold:
            flags.append(QualityFlag.POSSIBLE_GLARE.value)

        if width < self.min_width or height < self.min_height:
            flags.append(QualityFlag.LOW_RESOLUTION.value)

        # 6. Determine overall QualityStatus
        if len(flags) == 0:
            status = QualityStatus.GOOD
        elif (
            blur_score < 25.0
            or (QualityFlag.TOO_DARK.value in flags and QualityFlag.LOW_CONTRAST.value in flags)
            or (QualityFlag.TOO_BRIGHT.value in flags and QualityFlag.POSSIBLE_GLARE.value in flags and glare_score > 0.35)
        ):
            status = QualityStatus.UNREADABLE
        elif (
            len(flags) == 1
            and (QualityFlag.LOW_CONTRAST.value in flags or QualityFlag.LOW_RESOLUTION.value in flags)
            and blur_score >= 50.0
        ):
            status = QualityStatus.ACCEPTABLE
        else:
            status = QualityStatus.POOR

        return QualityAssessmentResult(
            width=width,
            height=height,
            channels=channels,
            blur_score=blur_score,
            brightness_score=brightness_score,
            contrast_score=contrast_score,
            glare_score=glare_score,
            flags=flags,
            status=status,
        )
