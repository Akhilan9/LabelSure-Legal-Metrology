import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_session
from app.models.user import Role, User

bearer = HTTPBearer(auto_error=False)


def unauthorized():
    return HTTPException(401, "Invalid or expired credentials", headers={"WWW-Authenticate": "Bearer"})


def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
                     session: Session = Depends(get_session)) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise unauthorized()
    try:
        claims = decode_token(credentials.credentials, request.app.state.settings)
    except jwt.InvalidTokenError:
        raise unauthorized()
    user = session.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise unauthorized()
    return user


def require_role(*roles: Role):
    """Explicit allowed roles; callers include ADMIN where administrative access applies."""
    def authorize(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "Your role does not permit this action")
        return user
    return authorize
