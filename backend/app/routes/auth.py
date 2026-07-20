from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

try:
    from backend.app.dependencies.auth import get_current_user
    from backend.app.models.schemas import AuthResponse, User, UserLogin, UserRegister
    from backend.app.services.auth import AuthError, create_access_token, user_repository
except ModuleNotFoundError:
    from app.dependencies.auth import get_current_user
    from app.models.schemas import AuthResponse, User, UserLogin, UserRegister
    from app.services.auth import AuthError, create_access_token, user_repository


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(payload: UserRegister) -> AuthResponse:
    try:
        normalized_username = payload.username.strip() if payload.username else ""
        if len(normalized_username) < 3:
            normalized_username = payload.email.split("@", 1)[0]
        user = user_repository.register(normalized_username, payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AuthResponse(access_token=create_access_token(user), user=user)


@router.post("/login", response_model=AuthResponse)
def login(payload: UserLogin) -> AuthResponse:
    try:
        user = user_repository.login(payload.email, payload.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return AuthResponse(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=User)
def me(current_user: User = Depends(get_current_user())) -> User:
    return current_user
