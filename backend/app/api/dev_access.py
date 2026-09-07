from fastapi import APIRouter, Depends

from app.api.dependencies import require_role
from app.models.user import Role, User

router = APIRouter(prefix="/dev/access", tags=["Development RBAC checks"])


@router.get("/admin")
def admin(user: User = Depends(require_role(Role.ADMIN))):
    return {"allowed": True, "role": user.role, "capability": "administration"}


@router.get("/inspection")
def inspection(user: User = Depends(require_role(Role.INSPECTOR, Role.ADMIN))):
    return {"allowed": True, "role": user.role, "capability": "inspection_creation"}


@router.get("/monitoring")
def monitoring(user: User = Depends(require_role(Role.SUPERVISOR, Role.ADMIN))):
    return {"allowed": True, "role": user.role, "capability": "monitoring"}
