from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from backend.app.models.schemas import User
    from backend.app.services.auth import AuthError, decode_access_token, user_repository
except ModuleNotFoundError:
    from app.models.schemas import User
    from app.services.auth import AuthError, decode_access_token, user_repository


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user() -> Callable[..., User]:
    def dependency(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> User:
        if credentials is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
        try:
            token_user = decode_access_token(credentials.credentials)
            return user_repository.get_by_id(token_user.user_id)
        except AuthError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return dependency
