from datetime import datetime, timezone
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import get_current_user, require_role
from app.db.session import get_session
from app.image_processing.pipeline import ImageProcessingPipeline
from app.image_processing.schemas import (
    BatchProcessImagesResponse,
    ImageQualityMetrics,
    ImageQualityResponse,
)
from app.models.image_quality import ImageProcessingResult, QualityStatus
from app.models.inspection import (
    ImportStatus,
    Inspection,
    InspectionImage,
    InspectionStatus,
    PanelType,
)
from app.models.user import Role, User
from app.ocr.schemas import (
    BatchOCRResponse,
    InspectionOCRSummary,
    OCRBlockResponse,
    OCRRunResponse,
)
from app.ocr.service import OCRService, to_ocr_run_response
from app.schemas.inspection import (
    InspectionCreate,
    InspectionImageResponse,
    InspectionImageUpdate,
    InspectionListResponse,
    InspectionResponse,
    InspectionUpdate,
)
from app.services.inspection import (
    can_access_inspection,
    can_modify_inspection,
    generate_inspection_code,
    is_inspection_editable,
)
from app.storage.service import (
    LocalStorageService,
    calculate_sha256,
    detect_and_validate_image,
)

from app.services.banned_products import check_international_bans

router = APIRouter(prefix="/inspections", tags=["Inspections"])


def to_quality_response(result: ImageProcessingResult, inspection_id: str) -> ImageQualityResponse:
    derived_available = result.derived_storage_path is not None
    derived_url = (
        f"/api/v1/inspections/{inspection_id}/images/{result.inspection_image_id}/processed"
        if derived_available
        else None
    )
    return ImageQualityResponse(
        id=result.id,
        inspection_image_id=result.inspection_image_id,
        quality_status=result.quality_status,
        width=result.width,
        height=result.height,
        channels=result.channels,
        metrics=ImageQualityMetrics(
            blur_score=result.blur_score,
            brightness_score=result.brightness_score,
            contrast_score=result.contrast_score,
            glare_score=result.glare_score,
        ),
        flags=result.quality_flags or [],
        processing_version=result.processing_version,
        derived_image_available=derived_available,
        derived_content_url=derived_url,
        derived_sha256=result.derived_sha256,
        error_message=result.error_message,
        processed_at=result.processed_at,
    )


def to_image_response(image: InspectionImage, inspection_id: str) -> InspectionImageResponse:
    proc_res = (
        to_quality_response(image.processing_result, inspection_id)
        if image.processing_result
        else None
    )
    return InspectionImageResponse(
        id=image.id,
        inspection_id=image.inspection_id,
        original_filename=image.original_filename,
        stored_filename=image.stored_filename,
        mime_type=image.mime_type,
        file_size=image.file_size,
        sha256=image.sha256,
        panel_type=image.panel_type,
        upload_order=image.upload_order,
        width=image.width,
        height=image.height,
        quality_status=image.quality_status,
        created_at=image.created_at,
        uploaded_by_user_id=image.uploaded_by_user_id,
        content_url=f"/api/v1/inspections/{inspection_id}/images/{image.id}/content",
        processing_result=proc_res,
    )


def to_inspection_response(inspection: Inspection) -> InspectionResponse:
    images_resp = [to_image_response(img, inspection.id) for img in inspection.images]
    prod_name = inspection.product_name
    if not prod_name and getattr(inspection, 'declarations', None):
        for d in inspection.declarations:
            if getattr(d, 'declaration_type', None) == 'COMMON_PRODUCT_NAME' and getattr(d, 'raw_value', None):
                prod_name = d.raw_value
                break

    resp = InspectionResponse(
        id=inspection.id,
        inspection_code=inspection.inspection_code,
        created_by_user_id=inspection.created_by_user_id,
        created_by_name=inspection.created_by.full_name if inspection.created_by else None,
        assigned_to_user_id=inspection.assigned_to_user_id,
        assigned_to_name=inspection.assigned_to.full_name if inspection.assigned_to else None,
        status=inspection.status,
        product_name=inspection.product_name or prod_name,
        brand_name=inspection.brand_name,
        category=inspection.category,
        package_type=inspection.package_type,
        import_status=inspection.import_status,
        barcode=inspection.barcode,
        manufacturer_name=inspection.manufacturer_name,
        packer_name=inspection.packer_name,
        importer_name=inspection.importer_name,
        notes=inspection.notes,
        images_count=len(inspection.images),
        images=images_resp,
        international_ban_info=check_international_bans(inspection.product_name or prod_name),
        created_at=inspection.created_at,
        updated_at=inspection.updated_at,
        submitted_at=inspection.submitted_at,
    )
    return resp


@router.post("", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
def create_inspection(
    payload: InspectionCreate,
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> InspectionResponse:
    if payload.client_id:
        existing = session.get(Inspection, str(payload.client_id))
        if existing:
            if existing.created_by_user_id != current_user.id: raise HTTPException(409, "Draft identifier is already in use")
            return to_inspection_response(existing)
    code = generate_inspection_code(session)
    inspection = Inspection(
        **({"id":str(payload.client_id)} if payload.client_id else {}),
        inspection_code=code,
        created_by_user_id=current_user.id,
        assigned_to_user_id=current_user.id if current_user.role == Role.INSPECTOR else None,
        status=InspectionStatus.DRAFT,
        product_name=payload.product_name,
        brand_name=payload.brand_name,
        category=payload.category,
        package_type=payload.package_type,
        import_status=payload.import_status,
        barcode=payload.barcode,
        manufacturer_name=payload.manufacturer_name,
        packer_name=payload.packer_name,
        importer_name=payload.importer_name,
        notes=payload.notes,
    )
    # Concurrent requests can reserve the same sequential code. Retry only that collision.
    for attempt in range(5):
        inspection.inspection_code = generate_inspection_code(session)
        session.add(inspection)
        try:
            session.commit()
            break
        except IntegrityError as exc:
            session.rollback()
            if "inspection_code" not in str(exc.orig):
                raise
            if attempt == 4:
                raise HTTPException(409, "Inspection numbering is busy. Please retry.") from exc
    session.refresh(inspection)
    return to_inspection_response(inspection)


@router.get("", response_model=InspectionListResponse)
def list_inspections(
    status_filter: InspectionStatus | None = Query(default=None, alias="status"),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> InspectionListResponse:
    stmt = select(Inspection)

    if current_user.role == Role.INSPECTOR:
        stmt = stmt.where(
            or_(
                Inspection.created_by_user_id == current_user.id,
                Inspection.assigned_to_user_id == current_user.id,
            )
        )

    if status_filter:
        stmt = stmt.where(Inspection.status == status_filter)

    if q and q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Inspection.inspection_code.ilike(term),
                Inspection.product_name.ilike(term),
                Inspection.brand_name.ilike(term),
                Inspection.barcode.ilike(term),
                Inspection.manufacturer_name.ilike(term),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.scalar(count_stmt) or 0

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Inspection.created_at.desc()).offset(offset).limit(page_size)
    inspections = session.scalars(stmt).all()

    items = [to_inspection_response(insp) for insp in inspections]
    return InspectionListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/{inspection_id}", response_model=InspectionResponse)
def get_inspection(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> InspectionResponse:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return to_inspection_response(inspection)


@router.patch("/{inspection_id}", response_model=InspectionResponse)
def update_inspection(
    inspection_id: str,
    payload: InspectionUpdate,
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> InspectionResponse:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to edit this inspection")

    if not is_inspection_editable(inspection):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inspection is in {inspection.status.value} status and cannot be modified",
        )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(inspection, field, value)

    inspection.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(inspection)
    return to_inspection_response(inspection)


@router.post("/{inspection_id}/images", response_model=list[InspectionImageResponse], status_code=status.HTTP_201_CREATED)
async def upload_inspection_images(
    inspection_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
    panel_types: list[str] = Form(default=[]),
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> list[InspectionImageResponse]:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this inspection")

    if not is_inspection_editable(inspection):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inspection is in {inspection.status.value} status and cannot accept new images",
        )

    settings = request.app.state.settings
    max_images = settings.max_images_per_inspection
    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024

    if len(files) == 0:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="No files provided for upload")

    if len(inspection.images) + len(files) > max_images:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Upload would exceed maximum of {max_images} images per inspection (currently {len(inspection.images)})",
        )

    storage = LocalStorageService(settings.storage_local_dir)
    created_images: list[InspectionImage] = []
    current_order_base = len(inspection.images)

    for idx, file in enumerate(files):
        try:
            content = await file.read()
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to read uploaded file")

        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{file.filename}' is empty (0 bytes)",
            )

        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{file.filename}' exceeds maximum allowed size of {settings.max_upload_size_mb} MB",
            )

        try:
            mime_type, ext = detect_and_validate_image(content, file.filename or "image.jpg")
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{file.filename}': {str(err)}",
            )

        # Parse panel type for this image
        flat_panels: list[str] = []
        for pt in panel_types:
            for item in str(pt).split(","):
                if item.strip():
                    flat_panels.append(item.strip())

        if idx < len(flat_panels) and flat_panels[idx]:
            try:
                chosen_panel = PanelType(flat_panels[idx].upper())
            except ValueError:
                chosen_panel = PanelType.OTHER
        elif len(files) == 2:
            chosen_panel = PanelType.FRONT if idx == 0 else PanelType.BACK
        elif len(inspection.images) >= 1:
            chosen_panel = PanelType.BACK
        else:
            chosen_panel = PanelType.FRONT

        sha256_hash = calculate_sha256(content)
        stored_filename, storage_path = storage.generate_storage_path(inspection.id, ext)
        storage.save_file(storage_path, content)

        image_record = InspectionImage(
            inspection_id=inspection.id,
            uploaded_by_user_id=current_user.id,
            original_filename=file.filename or f"image_{idx + 1}{ext}",
            stored_filename=stored_filename,
            storage_path=storage_path,
            mime_type=mime_type,
            file_size=len(content),
            sha256=sha256_hash,
            panel_type=chosen_panel,
            upload_order=current_order_base + idx,
        )
        session.add(image_record)
        session.flush()
        try:
            pipeline = ImageProcessingPipeline(settings, storage)
            decoded = pipeline.preprocessor.decode_and_orient(content)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"File '{file.filename}': {str(err)}",
            )
        assessed = pipeline.analyzer.analyze(decoded)
        image_record.width = assessed.width
        image_record.height = assessed.height
        image_record.quality_status = assessed.status.value
        session.add(ImageProcessingResult(
            inspection_image_id=image_record.id, width=assessed.width, height=assessed.height,
            channels=assessed.channels, blur_score=assessed.blur_score,
            brightness_score=assessed.brightness_score, contrast_score=assessed.contrast_score,
            glare_score=assessed.glare_score, quality_status=assessed.status,
            quality_flags=assessed.flags, processing_version=settings.image_pipeline_version,
        ))
        created_images.append(image_record)

    if inspection.status == InspectionStatus.DRAFT:
        inspection.status = InspectionStatus.EVIDENCE_UPLOADED

    inspection.updated_at = datetime.now(timezone.utc)
    session.commit()

    for img in created_images:
        session.refresh(img)

    return [to_image_response(img, inspection.id) for img in created_images]


@router.get("/{inspection_id}/images", response_model=list[InspectionImageResponse])
def list_inspection_images(
    inspection_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[InspectionImageResponse]:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")
    return [to_image_response(img, inspection.id) for img in inspection.images]


@router.get("/{inspection_id}/images/{image_id}/content")
def get_inspection_image_content(
    inspection_id: str,
    image_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    image = session.get(InspectionImage, image_id)
    if not image or image.inspection_id != inspection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    try:
        data = storage.read_file(image.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image file not found on storage")

    return Response(
        content=data,
        media_type=image.mime_type,
        headers={"Cache-Control": "private, max-age=3600"},
    )


@router.patch("/{inspection_id}/images/{image_id}", response_model=InspectionImageResponse)
def update_inspection_image(
    inspection_id: str,
    image_id: str,
    payload: InspectionImageUpdate,
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> InspectionImageResponse:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this inspection")

    if not is_inspection_editable(inspection):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inspection is in {inspection.status.value} status and cannot be modified",
        )

    image = session.get(InspectionImage, image_id)
    if not image or image.inspection_id != inspection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    if payload.panel_type is not None:
        image.panel_type = payload.panel_type
    if payload.upload_order is not None:
        image.upload_order = payload.upload_order

    inspection.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(image)
    return to_image_response(image, inspection.id)


@router.delete("/{inspection_id}/images/{image_id}")
def delete_inspection_image(
    inspection_id: str,
    image_id: str,
    request: Request,
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> dict:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to modify this inspection")

    if not is_inspection_editable(inspection):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inspection is in {inspection.status.value} status and cannot be modified",
        )

    image = session.get(InspectionImage, image_id)
    if not image or image.inspection_id != inspection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    storage.delete_file(image.storage_path)

    # Also clean up derived artifact if it exists
    if image.processing_result and image.processing_result.derived_storage_path:
        storage.delete_file(image.processing_result.derived_storage_path)

    session.delete(image)
    session.flush()

    # Re-check remaining images count
    remaining_count = session.scalar(
        select(func.count(InspectionImage.id)).where(InspectionImage.inspection_id == inspection_id)
    )
    if remaining_count == 0 and inspection.status == InspectionStatus.EVIDENCE_UPLOADED:
        inspection.status = InspectionStatus.DRAFT

    inspection.updated_at = datetime.now(timezone.utc)
    session.commit()

    return {"detail": "Image deleted successfully"}


@router.post("/{inspection_id}/submit", response_model=InspectionResponse)
def submit_inspection(
    inspection_id: str,
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> InspectionResponse:
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to submit this inspection")

    if not is_inspection_editable(inspection):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Inspection is in {inspection.status.value} status and cannot be submitted again",
        )

    if len(inspection.images) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Inspection must have at least one uploaded evidence image before submission",
        )

    now = datetime.now(timezone.utc)
    inspection.status = InspectionStatus.READY_FOR_ANALYSIS
    inspection.submitted_at = now
    inspection.updated_at = now

    session.commit()
    session.refresh(inspection)
    return to_inspection_response(inspection)


# ====================================================================
# PHASE 4: Image Quality Assessment & OpenCV Preprocessing Endpoints
# ====================================================================


@router.post(
    "/{inspection_id}/images/{image_id}/process",
    response_model=ImageQualityResponse,
    status_code=status.HTTP_200_OK,
)
def process_single_image(
    inspection_id: str,
    image_id: str,
    request: Request,
    force: bool = Query(default=False, description="Force re-processing if already completed"),
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> ImageQualityResponse:
    """
    Executes OpenCV image quality assessment and preprocessing on a single package evidence image.
    """
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to process images in this inspection")

    image = session.get(InspectionImage, image_id)
    if not image or image.inspection_id != inspection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    pipeline = ImageProcessingPipeline(settings=request.app.state.settings)
    result = pipeline.process_image(image=image, session=session, force=force)

    return to_quality_response(result, inspection.id)


@router.post(
    "/{inspection_id}/process-images",
    response_model=BatchProcessImagesResponse,
    status_code=status.HTTP_200_OK,
)
def process_all_inspection_images(
    inspection_id: str,
    request: Request,
    force: bool = Query(default=False, description="Force re-processing of all images"),
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> BatchProcessImagesResponse:
    """
    Executes image quality assessment and preprocessing in batch for all evidence images of an inspection.
    """
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    if not can_modify_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to process images in this inspection")

    pipeline = ImageProcessingPipeline(settings=request.app.state.settings)
    results: list[ImageQualityResponse] = []
    successful = 0
    failed = 0

    for image in inspection.images:
        res = pipeline.process_image(image=image, session=session, force=force)
        if res.quality_status == QualityStatus.PROCESSING_FAILED:
            failed += 1
        else:
            successful += 1
        results.append(to_quality_response(res, inspection.id))

    return BatchProcessImagesResponse(
        total_processed=len(inspection.images),
        successful_count=successful,
        failed_count=failed,
        results=results,
    )


@router.get(
    "/{inspection_id}/images/{image_id}/quality",
    response_model=ImageQualityResponse,
    status_code=status.HTTP_200_OK,
)
def get_image_quality(
    inspection_id: str,
    image_id: str,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> ImageQualityResponse:
    """
    Retrieves the explainable image quality assessment metrics and flags for a specific image.
    """
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    image = session.get(InspectionImage, image_id)
    if not image or image.inspection_id != inspection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    if not image.processing_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image quality analysis has not been performed yet for this image",
        )

    return to_quality_response(image.processing_result, inspection.id)


@router.get("/{inspection_id}/images/{image_id}/processed")
def get_processed_image_content(
    inspection_id: str,
    image_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> Response:
    """
    Streams the derived preprocessed (OCR-ready) PNG image for authorized users.
    """
    inspection = session.get(Inspection, inspection_id)
    if not inspection or not can_access_inspection(current_user, inspection):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found")

    image = session.get(InspectionImage, image_id)
    if not image or image.inspection_id != inspection_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")

    if not image.processing_result or not image.processing_result.derived_storage_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Derived preprocessed image not found. Process the image first.",
        )

    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    try:
        data = storage.read_file(image.processing_result.derived_storage_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Preprocessed image file not found on storage",
        )

    return Response(
        content=data,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=3600"},
    )


# ====================================================================
# PHASE 5: OCR Engine & Evidence Text Extraction Endpoints
# ====================================================================


@router.post(
    "/{inspection_id}/images/{image_id}/ocr",
    response_model=OCRRunResponse,
    status_code=status.HTTP_200_OK,
)
def process_single_image_ocr(
    inspection_id: str,
    image_id: str,
    request: Request,
    force: bool = Query(default=False, description="Force re-execution of OCR recognition"),
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> OCRRunResponse:
    """
    Executes deep learning OCR text recognition on an evidence image.
    Uses Phase 4 preprocessed derived artifact if available, fallback to original evidence image.
    """
    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    service = OCRService(db=session, settings=settings, storage_service=storage)

    ocr_run = service.process_image_ocr(
        inspection_id=inspection_id,
        image_id=image_id,
        current_user=current_user,
        force=force,
    )
    return to_ocr_run_response(ocr_run)


@router.post(
    "/{inspection_id}/ocr",
    response_model=BatchOCRResponse,
    status_code=status.HTTP_200_OK,
)
def process_all_inspection_ocr(
    inspection_id: str,
    request: Request,
    force: bool = Query(default=False, description="Force re-execution of OCR for all images"),
    current_user: User = Depends(require_role(Role.INSPECTOR)),
    session: Session = Depends(get_session),
) -> BatchOCRResponse:
    """
    Executes batch OCR text extraction across all evidence images of an inspection.
    """
    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    service = OCRService(db=session, settings=settings, storage_service=storage)

    return service.batch_process_inspection_ocr(
        inspection_id=inspection_id,
        current_user=current_user,
        force=force,
    )


@router.get(
    "/{inspection_id}/images/{image_id}/ocr",
    response_model=OCRRunResponse,
    status_code=status.HTTP_200_OK,
)
def get_single_image_ocr(
    inspection_id: str,
    image_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> OCRRunResponse:
    """
    Retrieves the latest OCR run and bounding box text blocks for an evidence image.
    """
    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    service = OCRService(db=session, settings=settings, storage_service=storage)

    ocr_run = service.get_image_ocr_run(
        inspection_id=inspection_id,
        image_id=image_id,
        current_user=current_user,
    )
    return to_ocr_run_response(ocr_run)


@router.get(
    "/{inspection_id}/images/{image_id}/ocr/blocks",
    response_model=list[OCRBlockResponse],
    status_code=status.HTTP_200_OK,
)
def get_single_image_ocr_blocks(
    inspection_id: str,
    image_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[OCRBlockResponse]:
    """
    Retrieves the list of recognized text blocks for an image's latest OCR run.
    """
    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    service = OCRService(db=session, settings=settings, storage_service=storage)

    run = service.get_image_ocr_run(
        inspection_id=inspection_id,
        image_id=image_id,
        current_user=current_user,
    )
    resp = to_ocr_run_response(run)
    return resp.blocks


@router.get(
    "/{inspection_id}/ocr/summary",
    response_model=InspectionOCRSummary,
    status_code=status.HTTP_200_OK,
)
def get_inspection_ocr_summary(
    inspection_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> InspectionOCRSummary:
    """
    Retrieves an aggregate summary of OCR evidence across all panels of an inspection.
    """
    settings = request.app.state.settings
    storage = LocalStorageService(settings.storage_local_dir)
    service = OCRService(db=session, settings=settings, storage_service=storage)

    return service.get_inspection_ocr_summary(
        inspection_id=inspection_id,
        current_user=current_user,
    )


@router.get(
    "/{inspection_id}/color-marks",
    status_code=status.HTTP_200_OK,
)
def get_inspection_color_marks(
    inspection_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Scans and returns detected statutory color marks (Vegetarian green mark,
    Non-Vegetarian brown/red mark, Yellow warning mark, Blue fortification mark).
    """
    inspection = session.get(Inspection, inspection_id)
    if not inspection:
        raise HTTPException(404, "Inspection not found")
    if not can_access_inspection(current_user, inspection):
        raise HTTPException(403, "Forbidden")

    settings = request.app.state.settings
    from app.services.color_marks import scan_inspection_color_marks
    marks = scan_inspection_color_marks(inspection, settings.storage_local_dir)
    return {
        "inspection_id": inspection_id,
        "total_marks": len(marks),
        "detected_color_marks": marks,
    }

