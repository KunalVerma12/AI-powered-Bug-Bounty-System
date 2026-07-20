from __future__ import annotations

import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

try:
    from backend.app.dependencies.auth import get_current_user
    from backend.app.models.schemas import GitHubAuthStart, GitHubConnectionStatus, ScanApiResponse, User, WorkspaceOverview, WorkspaceRepository, WorkspaceScanRequest
    from backend.app.services.auth import AuthError, decode_access_token, user_repository
    from backend.app.services.github import FRONTEND_URL, GitHubIntegrationError, github_workspace_service
except ModuleNotFoundError:
    from app.dependencies.auth import get_current_user
    from app.models.schemas import GitHubAuthStart, GitHubConnectionStatus, ScanApiResponse, User, WorkspaceOverview, WorkspaceRepository, WorkspaceScanRequest
    from app.services.auth import AuthError, decode_access_token, user_repository
    from app.services.github import FRONTEND_URL, GitHubIntegrationError, github_workspace_service


router = APIRouter(tags=["github-workspace"])


def _frontend_redirect(params: dict[str, str]) -> str:
    return f"{FRONTEND_URL}/#{urllib.parse.urlencode(params)}"


def _optional_user_from_request(request: Request) -> User | None:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("bearer "):
        return None
    try:
        token_user = decode_access_token(header.split(" ", 1)[1])
        return user_repository.get_by_id(token_user.user_id)
    except AuthError:
        return None


@router.get("/github/status", response_model=GitHubConnectionStatus)
async def github_status(current_user: User = Depends(get_current_user())) -> GitHubConnectionStatus:
    return github_workspace_service.status(current_user.user_id)


@router.post("/github/connect", response_model=GitHubAuthStart)
async def github_connect(current_user: User = Depends(get_current_user())) -> GitHubAuthStart:
    try:
        return github_workspace_service.create_oauth_start(current_user)
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/auth/github/login", response_model=GitHubAuthStart)
async def github_login(request: Request) -> GitHubAuthStart:
    try:
        return github_workspace_service.create_oauth_start(_optional_user_from_request(request))
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/auth/github/login")
async def github_login_redirect() -> RedirectResponse:
    try:
        start = github_workspace_service.create_oauth_start(None)
        return RedirectResponse(start.auth_url)
    except GitHubIntegrationError as exc:
        return RedirectResponse(_frontend_redirect({"github": "error", "message": str(exc), "tab": "workspace"}))


@router.get("/auth/github/callback")
@router.get("/github/callback")
async def github_callback(code: str = Query(default=""), state: str = Query(default="")) -> RedirectResponse:
    try:
        if not code or not state:
            raise GitHubIntegrationError("GitHub OAuth callback is missing code or state.")
        user, token = await github_workspace_service.complete_oauth(code, state)
        return RedirectResponse(
            _frontend_redirect(
                {
                    "github": "connected",
                    "tab": "workspace",
                    "token": token,
                    "username": user.username,
                }
            )
        )
    except GitHubIntegrationError as exc:
        return RedirectResponse(_frontend_redirect({"github": "error", "message": str(exc), "tab": "workspace"}))


@router.get("/auth/github/me", response_model=GitHubConnectionStatus)
async def github_me(current_user: User = Depends(get_current_user())) -> GitHubConnectionStatus:
    return github_workspace_service.status(current_user.user_id)


@router.get("/github/repos", response_model=list[WorkspaceRepository])
async def github_repos(refresh: bool = False, current_user: User = Depends(get_current_user())) -> list[WorkspaceRepository]:
    try:
        overview = await github_workspace_service.workspace(current_user.user_id, refresh=refresh)
        return overview.repositories
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/github/disconnect")
async def github_disconnect(current_user: User = Depends(get_current_user())) -> dict[str, bool]:
    github_workspace_service.disconnect(current_user.user_id)
    return {"connected": False}


@router.get("/workspace", response_model=WorkspaceOverview)
async def workspace(refresh: bool = False, current_user: User = Depends(get_current_user())) -> WorkspaceOverview:
    try:
        return await github_workspace_service.workspace(current_user.user_id, refresh=refresh)
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/workspace/repositories/{repo_id}/scan", response_model=ScanApiResponse)
async def scan_workspace_repository(repo_id: str, payload: WorkspaceScanRequest, current_user: User = Depends(get_current_user())) -> ScanApiResponse:
    try:
        return github_workspace_service.launch_scan(current_user.user_id, repo_id, payload.preset)
    except GitHubIntegrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
