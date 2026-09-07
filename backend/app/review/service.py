from datetime import datetime
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.user import User, Role, utc_now
from app.models.inspection import Inspection
from app.models.rules import RuleEvaluationRun, RuleEvaluationResult
from app.models.review import (
    InspectionReview,
    RuleReviewDecision,
    DeclarationCorrection,
    OCRCorrection,
    AuditEvent
)
from app.review.schemas import (
    RuleDecisionRequest,
    DeclarationCorrectionRequest,
    OCRCorrectionRequest,
    FinalizeReviewRequest,
    ReopenReviewRequest
)


class ReviewService:
    def __init__(self, db: Session, settings=None):
        self.db = db
        self.settings = settings

    def _get_inspection_with_access(self, inspection_id: str, user: User, write: bool = False) -> Inspection:
        inspection = self.db.scalar(select(Inspection).where(Inspection.id == inspection_id))
        if not inspection:
            raise HTTPException(404, "Inspection not found")
        if user.role == Role.INSPECTOR and inspection.created_by_user_id != user.id:
            raise HTTPException(403, "Access restricted to the inspection owner")
        return inspection

    def _log_audit(
        self,
        inspection_id: str,
        user: User,
        action: str,
        entity_type: str,
        entity_id: str | None,
        before_state: dict | None,
        after_state: dict | None,
        reason: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> AuditEvent:
        event = AuditEvent(
            inspection_id=inspection_id,
            user_id=user.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent
        )
        self.db.add(event)
        return event

    def get_or_create_review(self, inspection_id: str, user: User) -> InspectionReview:
        self._get_inspection_with_access(inspection_id, user, write=False)
        review = self.db.scalar(
            select(InspectionReview)
            .where(InspectionReview.inspection_id == inspection_id)
            .order_by(InspectionReview.created_at.desc())
        )
        if review:
            return review


        # Create new draft review
        review = InspectionReview(
            inspection_id=inspection_id,
            reviewer_user_id=user.id,
            status="DRAFT"
        )
        self.db.add(review)
        self._log_audit(
            inspection_id=inspection_id,
            user=user,
            action="REVIEW_CREATED",
            entity_type="INSPECTION_REVIEW",
            entity_id=review.id,
            before_state=None,
            after_state={"status": "DRAFT"},
            reason="Inspector initiated human review session"
        )
        self.db.commit()
        return review

    def record_rule_decision(self, inspection_id: str, user: User, req: RuleDecisionRequest) -> RuleReviewDecision:
        self._get_inspection_with_access(inspection_id, user, write=True)
        review = self.get_or_create_review(inspection_id, user)

        if review.status == "FINALIZED":
            raise HTTPException(409, "Inspection review is FINALIZED and locked against modification")

        # Find machine verdict from latest evaluation run
        latest_eval = self.db.scalar(
            select(RuleEvaluationRun)
            .where(RuleEvaluationRun.inspection_id == inspection_id)
            .order_by(RuleEvaluationRun.created_at.desc())
        )
        original_verdict = "UNCERTAIN"
        if latest_eval:
            for r in latest_eval.results:
                if r.rule_key == req.rule_key or r.rule_id == req.rule_id:
                    original_verdict = r.verdict
                    break

        is_overridden = (req.final_verdict != original_verdict)
        if is_overridden and (not req.override_reason or len(req.override_reason.strip()) < 5):
            raise HTTPException(422, "An override reason of at least 5 characters is mandatory when changing a machine rule verdict")

        existing = self.db.scalar(
            select(RuleReviewDecision)
            .where(
                RuleReviewDecision.review_id == review.id,
                RuleReviewDecision.rule_key == req.rule_key
            )
        )

        before_state = None
        if existing:
            before_state = {
                "final_verdict": existing.final_verdict,
                "is_overridden": existing.is_overridden,
                "override_reason": existing.override_reason,
                "reviewer_notes": existing.reviewer_notes
            }
            existing.final_verdict = req.final_verdict
            existing.is_overridden = is_overridden
            existing.override_reason = req.override_reason
            existing.reviewer_notes = req.reviewer_notes
            decision = existing
        else:
            decision = RuleReviewDecision(
                review_id=review.id,
                rule_id=req.rule_id,
                rule_key=req.rule_key,
                original_verdict=original_verdict,
                final_verdict=req.final_verdict,
                is_overridden=is_overridden,
                override_reason=req.override_reason,
                reviewer_notes=req.reviewer_notes
            )
            self.db.add(decision)

        after_state = {
            "rule_key": req.rule_key,
            "original_verdict": original_verdict,
            "final_verdict": req.final_verdict,
            "is_overridden": is_overridden,
            "override_reason": req.override_reason
        }

        self._log_audit(
            inspection_id=inspection_id,
            user=user,
            action="RULE_OVERRIDE" if is_overridden else "RULE_DECISION_CONFIRMED",
            entity_type="RULE_REVIEW_DECISION",
            entity_id=decision.id,
            before_state=before_state,
            after_state=after_state,
            reason=req.override_reason or "Inspector recorded rule decision"
        )
        self.db.commit()
        return decision

    def record_declaration_correction(self, inspection_id: str, user: User, req: DeclarationCorrectionRequest) -> DeclarationCorrection:
        self._get_inspection_with_access(inspection_id, user, write=True)
        review = self.get_or_create_review(inspection_id, user)

        if review.status == "FINALIZED":
            raise HTTPException(409, "Inspection review is FINALIZED and locked against modification")

        correction = DeclarationCorrection(
            review_id=review.id,
            candidate_id=req.candidate_id,
            declaration_type=req.declaration_type,
            original_raw_value=req.original_raw_value,
            original_normalized_value=req.original_normalized_value,
            corrected_value=req.corrected_value,
            action=req.action,
            correction_reason=req.correction_reason
        )
        self.db.add(correction)
        self._log_audit(
            inspection_id=inspection_id,
            user=user,
            action=f"DECLARATION_{req.action}",
            entity_type="DECLARATION_CORRECTION",
            entity_id=correction.id,
            before_state={"raw": req.original_raw_value, "normalized": req.original_normalized_value},
            after_state={"corrected_value": req.corrected_value, "action": req.action},
            reason=req.correction_reason
        )
        self.db.commit()
        return correction

    def record_ocr_correction(self, inspection_id: str, user: User, req: OCRCorrectionRequest) -> OCRCorrection:
        self._get_inspection_with_access(inspection_id, user, write=True)
        review = self.get_or_create_review(inspection_id, user)

        if review.status == "FINALIZED":
            raise HTTPException(409, "Inspection review is FINALIZED and locked against modification")

        correction = OCRCorrection(
            review_id=review.id,
            ocr_block_id=req.ocr_block_id,
            inspection_image_id=req.inspection_image_id,
            original_text=req.original_text,
            corrected_text=req.corrected_text,
            action=req.action,
            correction_reason=req.correction_reason
        )
        self.db.add(correction)
        self._log_audit(
            inspection_id=inspection_id,
            user=user,
            action=f"OCR_{req.action}",
            entity_type="OCR_CORRECTION",
            entity_id=correction.id,
            before_state={"original_text": req.original_text},
            after_state={"corrected_text": req.corrected_text, "action": req.action},
            reason=req.correction_reason
        )
        self.db.commit()
        return correction

    def finalize_review(self, inspection_id: str, user: User, req: FinalizeReviewRequest) -> InspectionReview:
        self._get_inspection_with_access(inspection_id, user, write=True)
        review = self.get_or_create_review(inspection_id, user)

        if review.status == "FINALIZED":
            raise HTTPException(409, "Inspection review is already finalized")

        before_state = {"status": review.status, "final_compliance_status": review.final_compliance_status}
        review.status = "FINALIZED"
        review.final_compliance_status = req.final_compliance_status
        review.summary_notes = req.summary_notes
        review.finalized_at = utc_now()

        after_state = {
            "status": "FINALIZED",
            "final_compliance_status": req.final_compliance_status,
            "finalized_at": review.finalized_at.isoformat()
        }

        self._log_audit(
            inspection_id=inspection_id,
            user=user,
            action="REVIEW_FINALIZED",
            entity_type="INSPECTION_REVIEW",
            entity_id=review.id,
            before_state=before_state,
            after_state=after_state,
            reason=req.summary_notes or "Inspection review formally finalized"
        )
        self.db.commit()
        return review

    def reopen_review(self, inspection_id: str, user: User, req: ReopenReviewRequest) -> InspectionReview:
        self._get_inspection_with_access(inspection_id, user, write=True)

        review = self.get_or_create_review(inspection_id, user)
        if review.status != "FINALIZED":
            raise HTTPException(409, "Inspection review is not finalized")

        before_state = {"status": review.status, "final_compliance_status": review.final_compliance_status}
        review.status = "REOPENED"

        after_state = {"status": "REOPENED"}

        self._log_audit(
            inspection_id=inspection_id,
            user=user,
            action="REVIEW_REOPENED",
            entity_type="INSPECTION_REVIEW",
            entity_id=review.id,
            before_state=before_state,
            after_state=after_state,
            reason=req.reopen_reason
        )
        self.db.commit()
        return review

    def get_audit_trail(self, inspection_id: str, user: User) -> list[AuditEvent]:
        self._get_inspection_with_access(inspection_id, user, write=False)
        events = self.db.scalars(
            select(AuditEvent)
            .where(AuditEvent.inspection_id == inspection_id)
            .order_by(AuditEvent.created_at.asc())
        ).all()
        return list(events)
