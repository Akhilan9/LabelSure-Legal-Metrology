import logging
from datetime import datetime
from typing import Sequence
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.models.image_quality import ImageProcessingResult
from app.models.inspection import Inspection, InspectionImage
from app.models.ocr import OCRBlock, OCRConfidenceTier, OCRRun, OCRStatus
from app.models.user import Role, User, utc_now
from app.ocr.base import BaseOCRProvider
from app.ocr.normalization import determine_confidence_tier
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.providers.rapid import RapidOCRProvider
from app.ocr.schemas import (
    BatchOCRResponse,
    BoundingBoxDict,
    InspectionOCRSummary,
    InspectionOCRSummaryPanel,
    OCRBlockResponse,
    OCRRunResponse,
)
from app.services.inspection import can_access_inspection, can_modify_inspection
from app.storage.service import LocalStorageService

logger = logging.getLogger("labelsure.ocr.service")

# Global cached provider instance to avoid reloading models across requests
_GLOBAL_PROVIDER_INSTANCE: BaseOCRProvider | None = None
_GLOBAL_PROVIDER_TYPE: str | None = None


def check_inspection_access(db: Session, inspection_id: str, current_user: User) -> Inspection:
    """Helper to verify inspection existence and user read access."""
    inspection = db.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )
    return inspection


def get_ocr_provider(settings: Settings) -> BaseOCRProvider:
    """Returns the singleton OCR provider instance based on runtime settings."""
    global _GLOBAL_PROVIDER_INSTANCE, _GLOBAL_PROVIDER_TYPE

    if _GLOBAL_PROVIDER_INSTANCE is not None and _GLOBAL_PROVIDER_TYPE == "custom":
        return _GLOBAL_PROVIDER_INSTANCE

    provider_type = settings.ocr_provider.lower().strip()
    if _GLOBAL_PROVIDER_INSTANCE is not None and _GLOBAL_PROVIDER_TYPE == provider_type:
        return _GLOBAL_PROVIDER_INSTANCE

    if provider_type == "mock" and settings.environment == "test":
        _GLOBAL_PROVIDER_INSTANCE = MockOCRProvider()
    elif provider_type in {"rapid", "paddle"}:
        _GLOBAL_PROVIDER_INSTANCE = RapidOCRProvider()
    else:
        raise HTTPException(503, "Configure OCR_PROVIDER=rapid. Mock OCR is permitted only in tests.")

    _GLOBAL_PROVIDER_TYPE = provider_type
    return _GLOBAL_PROVIDER_INSTANCE


def set_custom_ocr_provider(provider: BaseOCRProvider | None) -> None:
    """Allows test fixtures to inject custom mock/stub providers."""
    global _GLOBAL_PROVIDER_INSTANCE, _GLOBAL_PROVIDER_TYPE
    _GLOBAL_PROVIDER_INSTANCE = provider
    _GLOBAL_PROVIDER_TYPE = "custom" if provider is not None else None


def to_ocr_run_response(run: OCRRun) -> OCRRunResponse:
    """Serializes ORM OCRRun to Pydantic response contract."""
    blocks_response = [
        OCRBlockResponse(
            relative_box=(lambda box, img: [box['x_min']/img.width, box['y_min']/img.height, box['width']/img.width, box['height']/img.height] if img and img.width and img.height else None)(b.bounding_box, getattr(run, 'image', None)),
            id=b.id,
            ocr_run_id=b.ocr_run_id,
            inspection_id=b.inspection_id,
            inspection_image_id=b.inspection_image_id,
            block_index=b.block_index,
            raw_text=b.raw_text,
            normalized_text=b.normalized_text,
            confidence=b.confidence,
            confidence_tier=b.confidence_tier,
            polygon=b.polygon,
            bounding_box=BoundingBoxDict(**b.bounding_box),
            line_number=b.line_number,
            reading_order=b.reading_order,
            created_at=b.created_at,
        )
        for b in (run.blocks or [])
    ]

    return OCRRunResponse(
        id=run.id,
        inspection_id=run.inspection_id,
        inspection_image_id=run.inspection_image_id,
        image_processing_result_id=run.image_processing_result_id,
        engine_name=run.engine_name,
        engine_version=run.engine_version,
        language_config=run.language_config,
        status=run.status,
        average_confidence=run.average_confidence,
        block_count=run.block_count,
        started_at=run.started_at,
        completed_at=run.completed_at,
        ocr_version=run.ocr_version,
        error_code=run.error_code,
        error_message_safe=run.error_message_safe,
        blocks=blocks_response,
    )


class OCRService:
    """Domain service managing OCR evidence acquisition and run persistence."""

    def __init__(self, db: Session, settings: Settings, storage_service: LocalStorageService):
        self.db = db
        self.settings = settings
        self.storage_service = storage_service

    def process_image_ocr(
        self,
        inspection_id: str,
        image_id: str,
        current_user: User,
        force: bool = False,
    ) -> OCRRun:
        """Executes OCR text recognition on an evidence image."""
        # 1. Authorize access
        inspection = check_inspection_access(self.db, inspection_id, current_user)

        if not can_modify_inspection(current_user, inspection):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to run OCR processing on this inspection",
            )

        # 2. Verify image belongs to inspection
        stmt = (
            select(InspectionImage)
            .where(
                InspectionImage.id == image_id,
                InspectionImage.inspection_id == inspection.id,
            )
            .options(selectinload(InspectionImage.processing_result))
        )
        image = self.db.scalar(stmt)
        if not image:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection image not found",
            )

        # 3. Check for Phase 4 preprocessing result (precondition)
        processing_result = image.processing_result
        target_storage_path = None

        if processing_result and processing_result.derived_storage_path:
            target_storage_path = processing_result.derived_storage_path
        else:
            # Check if derived file exists on disk
            _, candidate_derived_path = self.storage_service.generate_processed_storage_path(
                inspection_id=inspection.id, image_id=image.id
            )
            if self.storage_service.file_exists(candidate_derived_path):
                target_storage_path = candidate_derived_path
            else:
                # Fallback to original evidence image if preprocessing has not been run
                target_storage_path = image.storage_path

        # 4. Check idempotency (existing OCR run for same version)
        if not force:
            existing_run = self.db.scalar(
                select(OCRRun)
                .where(
                    OCRRun.inspection_image_id == image.id,
                    OCRRun.ocr_version == self.settings.ocr_pipeline_version,
                    OCRRun.status.in_([OCRStatus.SUCCESS, OCRStatus.PARTIAL]),
                )
                .options(selectinload(OCRRun.blocks))
                .order_by(desc(OCRRun.created_at))
            )
            if existing_run:
                logger.info("Returning existing cached OCR run for image %s", image.id)
                return existing_run

        # 5. Read image bytes safely
        try:
            image_bytes = self.storage_service.read_file(target_storage_path)
        except Exception as exc:
            logger.error("Failed to read image artifact at %s: %s", target_storage_path, exc)
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Evidence image artifact is missing or unreadable from storage",
            )

        # 6. Instantiate provider and execute OCR
        provider = get_ocr_provider(self.settings)
        started_at = utc_now()

        raw_result = provider.recognize_image_bytes(
            image_bytes=image_bytes,
            language=self.settings.ocr_language,
        )

        completed_at = utc_now()

        # 7. Persist OCRRun
        ocr_run = OCRRun(
            id=str(uuid4()),
            inspection_id=inspection.id,
            inspection_image_id=image.id,
            image_processing_result_id=processing_result.id if processing_result and processing_result.derived_storage_path and target_storage_path == processing_result.derived_storage_path else None,
            engine_name=raw_result.engine_name,
            engine_version=raw_result.engine_version,
            language_config=raw_result.language_config,
            status=raw_result.status,
            average_confidence=raw_result.average_confidence,
            block_count=len(raw_result.blocks),
            started_at=started_at,
            completed_at=completed_at,
            error_code=raw_result.error_code,
            error_message_safe=raw_result.error_message_safe,
            ocr_version=self.settings.ocr_pipeline_version,
        )
        self.db.add(ocr_run)
        self.db.flush()

        # 8. Persist OCRBlocks
        ocr_blocks: list[OCRBlock] = []
        for idx, block_data in enumerate(raw_result.blocks):
            tier = determine_confidence_tier(
                confidence=block_data.confidence,
                good_threshold=self.settings.ocr_confidence_good,
                review_threshold=self.settings.ocr_confidence_review,
            )
            ocr_block = OCRBlock(
                id=str(uuid4()),
                ocr_run_id=ocr_run.id,
                inspection_id=inspection.id,
                inspection_image_id=image.id,
                block_index=idx,
                raw_text=block_data.raw_text,
                normalized_text=block_data.normalized_text,
                confidence=block_data.confidence,
                confidence_tier=tier,
                polygon=block_data.polygon,
                bounding_box=block_data.bounding_box.model_dump(),
                line_number=block_data.line_number or (idx + 1),
                reading_order=block_data.reading_order if block_data.reading_order is not None else idx,
            )
            ocr_blocks.append(ocr_block)
            self.db.add(ocr_block)

        self.db.commit()
        self.db.refresh(ocr_run)
        ocr_run.blocks = ocr_blocks
        return ocr_run

    def batch_process_inspection_ocr(
        self,
        inspection_id: str,
        current_user: User,
        force: bool = False,
    ) -> BatchOCRResponse:
        """Runs OCR on all evidence images belonging to an inspection."""
        inspection = check_inspection_access(self.db, inspection_id, current_user)

        if not can_modify_inspection(current_user, inspection):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to run OCR processing on this inspection",
            )

        images = self.db.scalars(
            select(InspectionImage)
            .where(InspectionImage.inspection_id == inspection.id)
            .order_by(InspectionImage.upload_order)
        ).all()

        results: list[OCRRunResponse] = []
        success_count = 0
        partial_count = 0
        failed_count = 0

        for img in images:
            try:
                run = self.process_image_ocr(
                    inspection_id=inspection.id,
                    image_id=img.id,
                    current_user=current_user,
                    force=force,
                )
                resp = to_ocr_run_response(run)
                results.append(resp)

                if run.status == OCRStatus.SUCCESS:
                    success_count += 1
                elif run.status == OCRStatus.PARTIAL:
                    partial_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                logger.exception("Failed batch OCR for image %s: %s", img.id, exc)
                failed_count += 1
                # Create a synthetic error response item
                results.append(
                    OCRRunResponse(
                        id=str(uuid4()),
                        inspection_id=inspection.id,
                        inspection_image_id=img.id,
                        engine_name="PaddleOCR",
                        engine_version="3.7.0",
                        language_config=self.settings.ocr_language,
                        status=OCRStatus.FAILED,
                        started_at=utc_now(),
                        completed_at=utc_now(),
                        error_code="BATCH_OCR_IMAGE_ERROR",
                        error_message_safe="Failed to execute OCR on evidence image.",
                    )
                )

        return BatchOCRResponse(
            inspection_id=inspection.id,
            total_images=len(images),
            success=success_count,
            partial=partial_count,
            failed=failed_count,
            results=results,
        )

    def get_image_ocr_run(
        self,
        inspection_id: str,
        image_id: str,
        current_user: User,
    ) -> OCRRun:
        """Retrieves the latest OCR run for an evidence image."""
        inspection = check_inspection_access(self.db, inspection_id, current_user)

        # Verify image belongs to inspection
        image_exists = self.db.scalar(
            select(InspectionImage.id).where(
                InspectionImage.id == image_id,
                InspectionImage.inspection_id == inspection.id,
            )
        )
        if not image_exists:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection image not found",
            )

        run = self.db.scalar(
            select(OCRRun)
            .where(
                OCRRun.inspection_image_id == image_id,
                OCRRun.inspection_id == inspection.id,
            )
            .options(selectinload(OCRRun.blocks))
            .order_by(desc(OCRRun.created_at))
        )
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No OCR run found for this evidence image",
            )

        return run

    def get_image_ocr_blocks(
        self,
        inspection_id: str,
        image_id: str,
        current_user: User,
    ) -> list[OCRBlock]:
        """Retrieves the list of OCR text blocks for an image's latest OCR run."""
        run = self.get_image_ocr_run(inspection_id, image_id, current_user)
        return run.blocks or []

    def get_inspection_ocr_summary(
        self,
        inspection_id: str,
        current_user: User,
    ) -> InspectionOCRSummary:
        """Generates an aggregate summary of OCR evidence across all panels of an inspection."""
        inspection = check_inspection_access(self.db, inspection_id, current_user)

        images = self.db.scalars(
            select(InspectionImage)
            .where(InspectionImage.inspection_id == inspection.id)
            .options(selectinload(InspectionImage.processing_result))
            .order_by(InspectionImage.upload_order)
        ).all()

        total_images = len(images)
        processed_count = sum(1 for img in images if img.processing_result is not None)
        completed_ocr_count = 0
        failed_ocr_count = 0
        total_blocks_count = 0
        all_confidences: list[float] = []
        panels_summary: list[InspectionOCRSummaryPanel] = []

        for img in images:
            # Query latest run for each image
            latest_run = self.db.scalar(
                select(OCRRun)
                .where(
                    OCRRun.inspection_image_id == img.id,
                    OCRRun.inspection_id == inspection.id,
                )
                .options(selectinload(OCRRun.blocks))
                .order_by(desc(OCRRun.created_at))
            )

            if latest_run:
                if latest_run.status in (OCRStatus.SUCCESS, OCRStatus.PARTIAL):
                    completed_ocr_count += 1
                elif latest_run.status == OCRStatus.FAILED:
                    failed_ocr_count += 1

                blocks = latest_run.blocks or []
                total_blocks_count += len(blocks)
                text_lines = [b.normalized_text for b in blocks if b.normalized_text]

                for b in blocks:
                    all_confidences.append(b.confidence)

                panels_summary.append(
                    InspectionOCRSummaryPanel(
                        panel_type=img.panel_type.value if hasattr(img.panel_type, "value") else str(img.panel_type),
                        image_id=img.id,
                        ocr_run_id=latest_run.id,
                        status=latest_run.status,
                        block_count=len(blocks),
                        average_confidence=latest_run.average_confidence,
                        text_lines=text_lines,
                    )
                )
            else:
                panels_summary.append(
                    InspectionOCRSummaryPanel(
                        panel_type=img.panel_type.value if hasattr(img.panel_type, "value") else str(img.panel_type),
                        image_id=img.id,
                        ocr_run_id=None,
                        status=None,
                        block_count=0,
                        average_confidence=None,
                        text_lines=[],
                    )
                )

        overall_avg_conf = (
            round(sum(all_confidences) / len(all_confidences), 4) if all_confidences else None
        )

        return InspectionOCRSummary(
            inspection_id=inspection.id,
            inspection_code=inspection.inspection_code,
            total_images=total_images,
            images_processed=processed_count,
            ocr_completed_count=completed_ocr_count,
            ocr_failed_count=failed_ocr_count,
            total_ocr_blocks=total_blocks_count,
            average_confidence=overall_avg_conf,
            panels=panels_summary,
        )
