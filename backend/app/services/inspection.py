from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.inspection import (
    ImportStatus,
    Inspection,
    InspectionImage,
    InspectionStatus,
    PanelType,
)
from app.models.user import Role, User


def generate_inspection_code(session: Session, year: int | None = None) -> str:
    """
    Generate sequential human-readable code: INS-YYYY-XXXXXX (e.g. INS-2026-000001).
    """
    if year is None:
        year = datetime.now(timezone.utc).year
    prefix = f"INS-{year}-"
    codes = session.scalars(select(Inspection.inspection_code).where(
        Inspection.inspection_code.like(f"{prefix}%")))
    # Demo/imported codes may have a non-numeric suffix; they must not reset numbering.
    numbers = [int(code[len(prefix):]) for code in codes if code[len(prefix):].isascii() and code[len(prefix):].isdigit()]
    return f"{prefix}{max(numbers, default=0) + 1:06d}"



def can_access_inspection(user: User, inspection: Inspection) -> bool:
    if user.role in {Role.ADMIN, Role.SUPERVISOR}:
        return True
    return inspection.created_by_user_id == user.id or inspection.assigned_to_user_id == user.id


def can_modify_inspection(user: User, inspection: Inspection) -> bool:
    return inspection.created_by_user_id == user.id or inspection.assigned_to_user_id == user.id


def is_inspection_editable(inspection: Inspection) -> bool:
    return inspection.status in {InspectionStatus.DRAFT, InspectionStatus.EVIDENCE_UPLOADED}
