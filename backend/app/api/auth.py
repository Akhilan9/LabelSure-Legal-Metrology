from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, unauthorized
from app.core.security import dummy_hash, issue_token, signing_key, verify_password
from app.db.session import get_session
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, response: Response, session: Session = Depends(get_session)):
    settings = request.app.state.settings
    signing_key(settings)
    user = session.scalar(select(User).where(User.email == body.email))
    valid = verify_password(body.password.get_secret_value(), user.hashed_password if user else dummy_hash())
    if not valid or user is None or not user.is_active:
        raise unauthorized()
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(access_token=issue_token(user.id, settings),
                         expires_in=settings.access_token_expire_minutes * 60,
                         user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
def me(response: Response, user: User = Depends(get_current_user)):
    response.headers["Cache-Control"] = "no-store"
    return user
