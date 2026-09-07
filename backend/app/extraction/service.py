import hashlib
import json
from collections import defaultdict
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.models.ocr import OCRRun, OCRStatus
from app.models.extraction import ExtractionRun, DeclarationCandidate, DeclarationCandidateSource, ExtractionStatus, ReviewStatus
from app.models.user import Role, utc_now
from app.ocr.service import check_inspection_access
from app.extraction.engine import extract

MAX_BLOCKS = 5000
MAX_CANDIDATES = 1000

class ExtractionService:
    def __init__(self, db, settings):
        self.db, self.settings = db, settings

    def snapshot(self, inspection):
        runs = self.db.scalars(select(OCRRun).where(OCRRun.inspection_id == inspection.id)
                               .order_by(OCRRun.created_at.desc(), OCRRun.id.desc())).all()
        latest = {}
        for run in runs:
            latest.setdefault(run.inspection_image_id, run)
        images = {i.id: i for i in inspection.images}
        fingerprint = hashlib.sha256(json.dumps({
            "runs": sorted((k, r.id, r.status.value) for k, r in latest.items()),
            "panels": sorted((i.id, i.panel_type.value) for i in images.values()),
            "product_context": inspection.product_name
        }, sort_keys=True).encode()).hexdigest()
        return latest, images, fingerprint

    def current(self, inspection_id, user):
        inspection = check_inspection_access(self.db, inspection_id, user)
        _, _, fingerprint = self.snapshot(inspection)
        run = self.db.scalar(select(ExtractionRun).where(
            ExtractionRun.inspection_id == inspection.id,
            ExtractionRun.version == self.settings.extraction_pipeline_version,
            ExtractionRun.input_fingerprint == fingerprint))
        return run

    def run(self, inspection_id, user):
        inspection = check_inspection_access(self.db, inspection_id, user)
        if inspection.created_by_user_id != user.id:
            raise HTTPException(403, "Not authorized to extract declarations")
        latest, images, fingerprint = self.snapshot(inspection)
        cached = self.current(inspection_id, user)
        if cached:
            return cached
        usable = [r for r in latest.values() if r.status in {OCRStatus.SUCCESS, OCRStatus.PARTIAL} and r.blocks]
        if not usable:
            raise HTTPException(409, "Usable OCR evidence is required. Run OCR before extracting declarations.")
        if sum(len(r.blocks) for r in usable) > MAX_BLOCKS:
            raise HTTPException(422, "OCR evidence exceeds the 5000-block extraction limit")
        if any(len(b.raw_text) > 2048 for r in usable for b in r.blocks):
            raise HTTPException(422, "An OCR block exceeds the 2048-character extraction limit")
        warnings = []
        if len(usable) < len(images) or any(r.status == OCRStatus.PARTIAL for r in usable):
            warnings.append("Some image evidence has missing, partial, or failed OCR")
        run = ExtractionRun(inspection_id=inspection.id, version=self.settings.extraction_pipeline_version,
                            input_fingerprint=fingerprint, status=ExtractionStatus.PROCESSING, warnings=warnings)
        self.db.add(run)
        try:
            self.db.flush()
            candidates = []
            for ocr in usable:
                image = images.get(ocr.inspection_image_id)
                if not image:
                    continue
                blocks = sorted(ocr.blocks, key=lambda b: (b.reading_order if b.reading_order is not None else b.block_index, b.block_index))
                for item in extract(blocks, image.panel_type.value, inspection.product_name):
                    sources = item.pop("sources")
                    item["structured_value"]["_source_image_variant"] = "processed" if ocr.image_processing_result_id else "original"
                    candidate = DeclarationCandidate(**item, extraction_run_id=run.id, inspection_id=inspection.id,
                        source_ocr_run_id=ocr.id, source_ocr_block_id=sources[0].id,
                        source_image_id=image.id, panel_type=image.panel_type.value,
                        review_status=ReviewStatus.NEEDS_REVIEW if item["needs_review"] else ReviewStatus.AUTO_EXTRACTED,
                        is_primary=False)
                    candidate.sources = [DeclarationCandidateSource(ocr_block_id=b.id, sequence_order=i) for i, b in enumerate(sources)]
                    candidates.append(candidate)
            if len(candidates) > MAX_CANDIDATES:
                raise HTTPException(422, "OCR evidence exceeds the 1000-candidate extraction limit")
            grouped = defaultdict(list)
            from app.services.banned_products import check_international_bans
            for candidate in candidates:
                grouped[candidate.declaration_type].append(candidate)
                if candidate.declaration_type == "COMMON_PRODUCT_NAME":
                    candidate.structured_value["international_ban_info"] = check_international_bans(
                        candidate.normalized_value, inspection.product_name
                    )
            for kind, group in grouped.items():
                strong = [c for c in group if c.confidence_score >= .80]
                # Different contact channels and dates may intentionally coexist; expose as possible disagreement.
                conflict = len({c.normalized_value.casefold() for c in strong}) > 1
                if conflict:
                    for candidate in group:
                        candidate.needs_review = True
                        candidate.review_status = ReviewStatus.NEEDS_REVIEW
                        candidate.review_reasons = candidate.review_reasons + ["Conflicting candidates"]
                else:
                    max(group, key=lambda c: c.confidence_score).is_primary = True

            # Only unambiguous primary candidates may fill blank editable metadata.
            from app.services.inspection import is_inspection_editable
            fields = {
                "COMMON_PRODUCT_NAME": ("product_name", 255),
                "MANUFACTURER_NAME": ("manufacturer_name", 255),
                "PACKER_NAME": ("packer_name", 255),
                "IMPORTER_NAME": ("importer_name", 255),
                "BARCODE_OR_GTIN": ("barcode", 64),
            }
            if is_inspection_editable(inspection):
                for candidate in candidates:
                    field = fields.get(candidate.declaration_type)
                    if (field and candidate.is_primary
                            and len({c.normalized_value.casefold() for c in grouped[candidate.declaration_type]}) == 1
                            and not getattr(inspection, field[0])):
                        value = candidate.normalized_value
                        if value and len(value) <= field[1]:
                            setattr(inspection, field[0], value)
                # Autofill changes product context: keep this run discoverable and cached.
                _, _, run.input_fingerprint = self.snapshot(inspection)

            run.candidates = candidates
            run.candidate_count = len(candidates)
            run.status = ExtractionStatus.PARTIAL if warnings else ExtractionStatus.SUCCESS
            run.completed_at = utc_now()
            self.db.commit()
            self.db.refresh(run)
            return run
        except IntegrityError:
            self.db.rollback()
            cached = self.current(inspection_id, user)
            if cached:
                return cached
            raise
        except Exception:
            self.db.rollback()
            raise

    def candidate(self, inspection_id, candidate_id, user):
        check_inspection_access(self.db, inspection_id, user)
        candidate = self.db.scalar(select(DeclarationCandidate).where(
            DeclarationCandidate.id == candidate_id, DeclarationCandidate.inspection_id == inspection_id))
        if candidate is None:
            raise HTTPException(404, "Declaration candidate not found")
        return candidate

