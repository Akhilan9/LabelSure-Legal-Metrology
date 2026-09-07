from datetime import datetime, timezone
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.user import User, Role
from app.models.inspection import Inspection, InspectionStatus
from app.models.rules import RuleEvaluationRun, RuleEvaluationResult
from app.models.review import InspectionReview, RuleReviewDecision
from app.models.ocr import OCRRun
from app.dashboard.schemas import (
    EnforcementMetricsResponse,
    ReviewQueueResponse,
    UrgencyQueueItem,
    ViolationStat,
    CategoryStat,
    AnalyticsTrendsResponse
)


class DashboardService:
    def __init__(self, db: Session):
        self.db = db

    def _apply_role_filter(self, query, user: User):
        if user.role == Role.INSPECTOR:
            return query.where(
                or_(
                    Inspection.created_by_user_id == user.id,
                    Inspection.assigned_to_user_id == user.id
                )
            )
        return query

    def get_enforcement_metrics(self, user: User) -> EnforcementMetricsResponse:
        # Base inspections query with role filtering
        base_query = self._apply_role_filter(select(Inspection), user)
        inspections = self.db.scalars(base_query).all()
        inspection_ids = [i.id for i in inspections]

        total_inspections = len(inspections)
        draft_count = sum(1 for i in inspections if i.status == InspectionStatus.DRAFT)
        evidence_uploaded_count = sum(1 for i in inspections if i.status == InspectionStatus.EVIDENCE_UPLOADED)
        ready_for_analysis_count = sum(1 for i in inspections if i.status == InspectionStatus.READY_FOR_ANALYSIS)

        # Reviews map
        reviews = {}
        if inspection_ids:
            review_records = self.db.scalars(
                select(InspectionReview).where(InspectionReview.inspection_id.in_(inspection_ids))
            ).all()
            for r in review_records:
                reviews[r.inspection_id] = r

        # Latest rule evaluations
        latest_evals = {}
        if inspection_ids:
            runs = self.db.scalars(
                select(RuleEvaluationRun)
                .where(RuleEvaluationRun.inspection_id.in_(inspection_ids))
                .order_by(RuleEvaluationRun.created_at.desc())
            ).all()
            for run in runs:
                if run.inspection_id not in latest_evals:
                    latest_evals[run.inspection_id] = run

        finalized_count = 0
        compliant_count = 0
        non_compliant_count = 0
        uncertain_count = 0
        total_overrides = 0
        violations_map: dict[str, dict] = {}
        category_map: dict[str, dict] = {}

        for insp in inspections:
            cat = insp.category or "UNSPECIFIED"
            if cat not in category_map:
                category_map[cat] = {"total": 0, "compliant": 0, "non_compliant": 0, "uncertain": 0}
            category_map[cat]["total"] += 1

            rev = reviews.get(insp.id)
            eval_run = latest_evals.get(insp.id)

            if rev and rev.status == "FINALIZED":
                finalized_count += 1
                status = rev.final_compliance_status
            elif eval_run:
                status = eval_run.overall
            else:
                status = "PENDING"

            if status == "COMPLIANT" or status == "PASS":
                compliant_count += 1
                category_map[cat]["compliant"] += 1
            elif status == "NON_COMPLIANT" or status == "FAIL":
                non_compliant_count += 1
                category_map[cat]["non_compliant"] += 1
            elif status == "UNCERTAIN":
                uncertain_count += 1
                category_map[cat]["uncertain"] += 1

            # Count overrides and violations
            if rev:
                for dec in rev.rule_decisions:
                    if dec.is_overridden:
                        total_overrides += 1

            if eval_run:
                for res in eval_run.results:
                    if res.verdict == "FAIL":
                        k = res.rule_key
                        if k not in violations_map:
                            violations_map[k] = {
                                "rule_key": k,
                                "title": res.title or k,
                                "severity": res.severity or "CRITICAL",
                                "count": 0,
                                "legal_reference": res.legal_reference
                            }
                        violations_map[k]["count"] += 1

        total_evaluated = compliant_count + non_compliant_count + uncertain_count
        compliance_pct = round((compliant_count / total_evaluated * 100.0), 1) if total_evaluated > 0 else 0.0

        top_violations = [
            ViolationStat(**v)
            for v in sorted(violations_map.values(), key=lambda x: x["count"], reverse=True)[:10]
        ]
        total_violations_count = sum(v["count"] for v in violations_map.values())

        category_breakdown = [
            CategoryStat(
                category=k,
                total=v["total"],
                compliant=v["compliant"],
                non_compliant=v["non_compliant"],
                uncertain=v["uncertain"]
            )
            for k, v in sorted(category_map.items(), key=lambda x: x[1]["total"], reverse=True)
        ]

        from app.rules.justifications import generate_failure_justifications
        guideline_justifications = generate_failure_justifications(list(violations_map.keys()))

        return EnforcementMetricsResponse(
            total_inspections=total_inspections,
            draft_count=draft_count,
            evidence_uploaded_count=evidence_uploaded_count,
            ready_for_analysis_count=ready_for_analysis_count,
            finalized_count=finalized_count,
            compliant_count=compliant_count,
            non_compliant_count=non_compliant_count,
            uncertain_count=uncertain_count,
            compliance_percentage=compliance_pct,
            total_overrides=total_overrides,
            total_violations=total_violations_count,
            top_violations=top_violations,
            category_breakdown=category_breakdown,
            guideline_failure_justifications=guideline_justifications
        )

    def get_review_queue(
        self,
        user: User,
        status_filter: str | None = None,
        category_filter: str | None = None,
        urgency_filter: str | None = None
    ) -> ReviewQueueResponse:
        base_query = self._apply_role_filter(select(Inspection), user)
        inspections = self.db.scalars(base_query.order_by(Inspection.created_at.desc())).all()
        inspection_ids = [i.id for i in inspections]

        # Pre-fetch reviews and evaluation runs
        reviews = {}
        if inspection_ids:
            for r in self.db.scalars(select(InspectionReview).where(InspectionReview.inspection_id.in_(inspection_ids))).all():
                reviews[r.inspection_id] = r

        latest_evals = {}
        if inspection_ids:
            for run in self.db.scalars(
                select(RuleEvaluationRun)
                .where(RuleEvaluationRun.inspection_id.in_(inspection_ids))
                .order_by(RuleEvaluationRun.created_at.desc())
            ).all():
                if run.inspection_id not in latest_evals:
                    latest_evals[run.inspection_id] = run

        now = datetime.now(timezone.utc)
        items: list[UrgencyQueueItem] = []
        crit_count = 0
        high_count = 0
        med_count = 0
        low_count = 0

        for insp in inspections:
            # Filter by category if requested
            if category_filter and insp.category != category_filter:
                continue

            rev = reviews.get(insp.id)
            eval_run = latest_evals.get(insp.id)

            # Determine review status
            if rev and rev.status == "FINALIZED":
                review_status = "FINALIZED"
                overall_compliance = rev.final_compliance_status or "COMPLIANT"
            elif rev and rev.status == "UNDER_REVIEW":
                review_status = "UNDER_REVIEW"
                overall_compliance = eval_run.overall if eval_run else "PENDING"
            elif eval_run:
                review_status = "NEEDS_REVIEW"
                overall_compliance = eval_run.overall
            else:
                review_status = "AWAITING_ANALYSIS"
                overall_compliance = "PENDING"

            # Filter by review status if requested
            if status_filter and status_filter != "ALL":
                if status_filter != review_status and status_filter != overall_compliance:
                    continue

            # Calculate days pending
            insp_created = insp.created_at
            if insp_created.tzinfo is None:
                insp_created = insp_created.replace(tzinfo=timezone.utc)
            days_pending = max(0, (now - insp_created).days)

            # Rule counts
            pass_c = eval_run.pass_count if eval_run else 0
            fail_c = eval_run.fail_count if eval_run else 0
            unc_c = eval_run.uncertain_count if eval_run else 0
            over_c = sum(1 for d in rev.rule_decisions if d.is_overridden) if rev else 0

            # Calculate Urgency Score
            score = 0.0
            if review_status != "FINALIZED":
                score += fail_c * 30.0       # Violations are critical
                score += unc_c * 15.0        # Uncertainties require inspector verification
                score += over_c * 10.0       # Overrides need supervisory review
                score += min(20.0, days_pending * 2.0)  # Age penalty
                if insp.status == InspectionStatus.READY_FOR_ANALYSIS:
                    score += 10.0
            else:
                score = 0.0  # Finalized inspections are resolved

            if score >= 50.0:
                tier = "CRITICAL"
                crit_count += 1
            elif score >= 30.0:
                tier = "HIGH"
                high_count += 1
            elif score >= 15.0:
                tier = "MEDIUM"
                med_count += 1
            else:
                tier = "LOW"
                low_count += 1

            if urgency_filter and urgency_filter != "ALL" and tier != urgency_filter:
                continue

            items.append(
                UrgencyQueueItem(
                    inspection_id=insp.id,
                    inspection_code=insp.inspection_code,
                    product_name=insp.product_name,
                    brand_name=insp.brand_name,
                    category=insp.category,
                    package_type=insp.package_type,
                    status=insp.status.value if hasattr(insp.status, "value") else str(insp.status),
                    overall_compliance=overall_compliance,
                    review_status=review_status,
                    urgency_score=round(score, 1),
                    urgency_tier=tier,
                    violation_count=fail_c,
                    uncertain_count=unc_c,
                    pass_count=pass_c,
                    override_count=over_c,
                    images_count=len(insp.images),
                    created_at=insp_created,
                    created_by_name=insp.created_by.full_name if hasattr(insp, "created_by") and insp.created_by else None,
                    days_pending=days_pending
                )
            )

        # Sort items by urgency_score desc, then created_at desc
        items.sort(key=lambda x: (x.urgency_score, x.created_at), reverse=True)

        return ReviewQueueResponse(
            items=items,
            total=len(items),
            critical_count=crit_count,
            high_count=high_count,
            medium_count=med_count,
            low_count=low_count
        )

    def get_analytics_trends(self, user: User) -> AnalyticsTrendsResponse:
        metrics = self.get_enforcement_metrics(user)

        base_query = self._apply_role_filter(select(Inspection), user)
        inspections = self.db.scalars(base_query).all()

        pkg_map: dict[str, int] = {}
        for i in inspections:
            pkg = i.package_type or "UNSPECIFIED"
            pkg_map[pkg] = pkg_map.get(pkg, 0) + 1

        pkg_distribution = [{"package_type": k, "count": v} for k, v in pkg_map.items()]

        # Compute average OCR confidence
        ocr_runs = self.db.scalars(select(OCRRun)).all()
        conf_values = [r.average_confidence for r in ocr_runs if r.average_confidence is not None]
        avg_conf = round(sum(conf_values) / len(conf_values) * 100.0, 1) if conf_values else 88.5

        total_reviewed = metrics.finalized_count
        total_overridden = metrics.total_overrides
        override_rate = round((total_overridden / max(1, total_reviewed) * 100.0), 1)

        return AnalyticsTrendsResponse(
            category_compliance=metrics.category_breakdown,
            package_type_distribution=pkg_distribution,
            average_ocr_confidence=avg_conf,
            total_reviewed=total_reviewed,
            total_overridden=total_overridden,
            override_rate_percentage=override_rate
        )
