from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.image_processing.preprocessing import ImagePreprocessor
from app.image_processing.quality import ImageQualityAnalyzer
from app.models.image_quality import ImageProcessingResult, QualityFlag, QualityStatus
from app.models.inspection import InspectionImage
from app.models.user import utc_now
from app.storage.service import LocalStorageService, calculate_sha256

logger = logging.getLogger(__name__)


@dataclass
class ProcessedArtifact:
    result: ImageProcessingResult
    derived_bytes: bytes | None = None


class ImageProcessingPipeline:
    def __init__(self, settings: Settings, storage: LocalStorageService | None = None):
        self.settings = settings
        self.storage = storage or LocalStorageService(settings.storage_local_dir)
        self.analyzer = ImageQualityAnalyzer(
            min_width=settings.image_min_width,
            min_height=settings.image_min_height,
            blur_threshold=settings.blur_threshold,
            brightness_low_threshold=settings.brightness_low_threshold,
            brightness_high_threshold=settings.brightness_high_threshold,
            contrast_threshold=settings.contrast_threshold,
            glare_pixel_threshold=settings.glare_pixel_threshold,
            glare_ratio_threshold=settings.glare_ratio_threshold,
        )
        self.preprocessor = ImagePreprocessor()

    def process_image(
        self,
        image: InspectionImage,
        session: Session,
        force: bool = False,
    ) -> ImageProcessingResult:
        """
        Executes the Phase 4 image quality assessment and OpenCV preprocessing pipeline.

        Idempotent: If the image was already successfully processed under the same pipeline
        version, returns the existing record unless `force=True`.
        """
        existing = image.processing_result
        if (
            existing
            and existing.processing_version == self.settings.image_pipeline_version
            and existing.quality_status != QualityStatus.PROCESSING_FAILED
            and not force
        ):
            return existing

        now = utc_now()

        try:
            # 1. Load original evidence bytes
            original_bytes = self.storage.read_file(image.storage_path)

            # 2. Decode safely and handle EXIF orientation
            cv_img = self.preprocessor.decode_and_orient(original_bytes)

            # 3. Assess quality signals (Blur, Brightness, Contrast, Glare, Resolution)
            quality_res = self.analyzer.analyze(cv_img)

            # 4. Generate derived OCR-ready artifact
            _, png_bytes = self.preprocessor.preprocess(cv_img)

            # 5. Store derived artifact separately
            filename, derived_path = self.storage.generate_processed_storage_path(
                inspection_id=image.inspection_id,
                image_id=image.id,
                filename="ocr_ready.png",
            )
            self.storage.save_file(derived_path, png_bytes)
            derived_sha = calculate_sha256(png_bytes)

            # 6. Update or create ImageProcessingResult record
            if existing:
                result_record = existing
                result_record.width = quality_res.width
                result_record.height = quality_res.height
                result_record.channels = quality_res.channels
                result_record.blur_score = quality_res.blur_score
                result_record.brightness_score = quality_res.brightness_score
                result_record.contrast_score = quality_res.contrast_score
                result_record.glare_score = quality_res.glare_score
                result_record.quality_status = quality_res.status
                result_record.quality_flags = quality_res.flags
                result_record.derived_storage_path = derived_path
                result_record.derived_filename = filename
                result_record.derived_sha256 = derived_sha
                result_record.processing_version = self.settings.image_pipeline_version
                result_record.error_message = None
                result_record.processed_at = now
                result_record.updated_at = now
            else:
                result_record = ImageProcessingResult(
                    inspection_image_id=image.id,
                    width=quality_res.width,
                    height=quality_res.height,
                    channels=quality_res.channels,
                    blur_score=quality_res.blur_score,
                    brightness_score=quality_res.brightness_score,
                    contrast_score=quality_res.contrast_score,
                    glare_score=quality_res.glare_score,
                    quality_status=quality_res.status,
                    quality_flags=quality_res.flags,
                    derived_storage_path=derived_path,
                    derived_filename=filename,
                    derived_sha256=derived_sha,
                    processing_version=self.settings.image_pipeline_version,
                    error_message=None,
                    processed_at=now,
                )
                session.add(result_record)

            # Also update cache fields on image record
            image.width = quality_res.width
            image.height = quality_res.height
            image.quality_status = quality_res.status.value

            session.commit()
            session.refresh(result_record)
            return result_record

        except Exception as err:
            logger.exception("Image processing failed for image ID %s", image.id)
            session.rollback()

            error_msg = str(err)
            flags = [QualityFlag.PROCESSING_ERROR.value]

            if existing:
                result_record = existing
                result_record.quality_status = QualityStatus.PROCESSING_FAILED
                result_record.quality_flags = flags
                result_record.error_message = error_msg
                result_record.processing_version = self.settings.image_pipeline_version
                result_record.processed_at = now
                result_record.updated_at = now
            else:
                result_record = ImageProcessingResult(
                    inspection_image_id=image.id,
                    width=0,
                    height=0,
                    channels=0,
                    blur_score=None,
                    brightness_score=None,
                    contrast_score=None,
                    glare_score=None,
                    quality_status=QualityStatus.PROCESSING_FAILED,
                    quality_flags=flags,
                    derived_storage_path=None,
                    derived_filename=None,
                    derived_sha256=None,
                    processing_version=self.settings.image_pipeline_version,
                    error_message=error_msg,
                    processed_at=now,
                )
                session.add(result_record)

            image.quality_status = QualityStatus.PROCESSING_FAILED.value
            session.commit()
            session.refresh(result_record)
            return result_record
