from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import urllib.error
import urllib.parse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from cryptography.fernet import Fernet
except ModuleNotFoundError:  # pragma: no cover - dependency should be installed in normal app runtime
    Fernet = None

try:
    from backend.app.models.schemas import (
        GitHubAuthStart,
        GitHubConnectionStatus,
        GitHubRepositoryProfile,
        ScanApiResponse,
        ScanPreset,
        User,
        WorkspaceAnalytics,
        WorkspaceOverview,
        WorkspaceRepository,
    )
    from backend.app.services.auth import SECRET_KEY, create_access_token, user_repository
    from backend.app.services.database import get_collection
    from backend.app.services.jobs import scan_job_service
    from backend.app.services.repository import scan_repository
except ModuleNotFoundError:
    from app.models.schemas import (
        GitHubAuthStart,
        GitHubConnectionStatus,
        GitHubRepositoryProfile,
        ScanApiResponse,
        ScanPreset,
        User,
        WorkspaceAnalytics,
        WorkspaceOverview,
        WorkspaceRepository,
    )
    from app.services.auth import SECRET_KEY, create_access_token, user_repository
    from app.services.database import get_collection
    from app.services.jobs import scan_job_service
    from app.services.repository import scan_repository


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env")

GITHUB_CLIENT_ID = os.environ.get("GITHUB_CLIENT_ID", "").strip()
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "").strip()
GITHUB_OAUTH_REDIRECT_URI = (
    os.environ.get("GITHUB_REDIRECT_URI")
    or os.environ.get("GITHUB_OAUTH_REDIRECT_URI")
    or "http://127.0.0.1:8000/github/callback"
).strip()
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://127.0.0.1:5173")
GITHUB_API = "https://api.github.com"
PLACEHOLDER_VALUES = {
    "",
    "YOUR_CLIENT_ID",
    "YOUR_CLIENT_SECRET",
    "your_client_id",
    "your_client_secret",
    "REPLACE_ME",
    "replace_me",
}


class GitHubIntegrationError(Exception):
    """Raised when GitHub workspace integration cannot proceed."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token_cipher():
    if Fernet is None:
        raise GitHubIntegrationError("Token encryption dependency is unavailable.")
    key = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode("utf-8")).digest())
    return Fernet(key)


def _encrypt_token(token: str) -> str:
    return _token_cipher().encrypt(token.encode("utf-8")).decode("utf-8")


def _decrypt_token(value: str) -> str:
    return _token_cipher().decrypt(value.encode("utf-8")).decode("utf-8")


def _json_request(url: str, *, method: str = "GET", token: str | None = None, data: dict[str, Any] | None = None) -> dict[str, Any] | list[Any]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "bug-bounty-hunter-workspace",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        response = requests.request(method, url, headers=headers, json=data, timeout=15)
        response.raise_for_status()
        return response.json() if response.content else {}
    except requests.HTTPError as exc:
        detail = response.text if "response" in locals() else str(exc)
        raise GitHubIntegrationError(f"GitHub API request failed: {detail}") from exc
    except requests.RequestException as exc:
        raise GitHubIntegrationError("GitHub API is unreachable from the backend.") from exc


def _parse_datetime(value: str | None) -> datetime:
    if not value:
        return _now()
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _repo_id(full_name: str) -> str:
    return base64.urlsafe_b64encode(full_name.encode("utf-8")).rstrip(b"=").decode("utf-8")


def _full_name_from_id(repo_id: str) -> str:
    padding = "=" * (-len(repo_id) % 4)
    return base64.urlsafe_b64decode(repo_id + padding).decode("utf-8")


def _authenticated_clone_url(html_url: str, token: str) -> str:
    parsed = urllib.parse.urlparse(html_url)
    quoted = urllib.parse.quote(token, safe="")
    return urllib.parse.urlunparse((parsed.scheme, f"x-access-token:{quoted}@{parsed.hostname}", parsed.path, "", "", ""))


def _profile_repository(repo: dict[str, Any], scans: list[ScanApiResponse], findings_count: int, critical_count: int, high_count: int) -> tuple[str, GitHubRepositoryProfile, int, int]:
    language = repo.get("language") or "multi-language"
    topics = repo.get("topics") or []
    private = bool(repo.get("private"))
    description = repo.get("description") or ""
    risk_words = " ".join([description, language, *topics]).lower()
    api_complexity = "Moderate API complexity"
    if any(word in risk_words for word in ["api", "server", "backend", "graphql", "gateway", "service"]):
        api_complexity = "Likely API-facing service with externally reachable routes"
    auth_quality = "Authentication quality needs review"
    if any(word in risk_words for word in ["auth", "oauth", "jwt", "session", "identity"]):
        auth_quality = "Authentication code is likely present and should be reviewed for middleware coverage"
    config_risk = "Configuration exposure risk is normal"
    if any(word in risk_words for word in ["config", "terraform", "docker", "k8s", "secret", "infra"]):
        config_risk = "Configuration and deployment files may expose sensitive defaults"
    dependency_risk = "Dependency risk is unknown until dependency-focused scan runs"
    if language.lower() in {"javascript", "typescript", "python", "ruby", "java"}:
        dependency_risk = f"{language} dependency manifests should be checked for vulnerable packages and stale lockfiles"
    maturity = "Emerging security maturity"
    if scans and findings_count == 0:
        maturity = "Healthy baseline from recent scans"
    elif critical_count or high_count > 2:
        maturity = "Needs focused remediation before it should be treated as mature"

    attack_surface_score = min(100, 18 + len(topics) * 4 + (18 if private else 8) + findings_count * 7 + critical_count * 18 + high_count * 10)
    security_posture = max(5, min(96, 88 - findings_count * 5 - critical_count * 18 - high_count * 10 + min(len(scans), 3) * 5))
    summary = (
        f"{repo.get('full_name')} appears to be a {language} repository. "
        f"{api_complexity}. {config_risk}. {dependency_risk}."
    )
    return summary, GitHubRepositoryProfile(
        architecture_summary=f"Likely {language} application or library based on GitHub metadata and repository topics.",
        auth_quality=auth_quality,
        config_exposure_risk=config_risk,
        api_complexity=api_complexity,
        dependency_risk=dependency_risk,
        security_maturity=maturity,
    ), attack_surface_score, security_posture


class GitHubWorkspaceService:
    def __init__(self) -> None:
        self._connections: dict[str, dict[str, Any]] = {}
        self._states: dict[str, dict[str, Any]] = {}
        self._repos: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)

    def _connections_collection(self):
        return get_collection("github_connections")

    def _states_collection(self):
        return get_collection("github_oauth_states")

    def _repos_collection(self):
        return get_collection("github_repositories")

    def configured(self) -> bool:
        return GITHUB_CLIENT_ID not in PLACEHOLDER_VALUES and GITHUB_CLIENT_SECRET not in PLACEHOLDER_VALUES

    def create_oauth_start(self, user: User | None = None) -> GitHubAuthStart:
        if not self.configured():
            raise GitHubIntegrationError(
                "GitHub OAuth is not configured. Set real GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET values in .env or your shell, then restart the backend."
            )
        state = secrets.token_urlsafe(32)
        record = {"state": state, "user_id": user.user_id if user else "", "created_at": _now().isoformat()}
        self._states[state] = record
        collection = self._states_collection()
        if collection is not None:
            collection.replace_one({"state": state}, record, upsert=True)
        query = urllib.parse.urlencode(
            {
                "client_id": GITHUB_CLIENT_ID,
                "redirect_uri": GITHUB_OAUTH_REDIRECT_URI,
                "scope": "read:user user:email repo",
                "state": state,
                "allow_signup": "true",
            }
        )
        return GitHubAuthStart(auth_url=f"https://github.com/login/oauth/authorize?{query}", state=state)

    async def complete_oauth(self, code: str, state: str) -> tuple[User, str]:
        state_record = self._load_state(state)
        token_payload = await self._exchange_code(code)
        access_token = token_payload.get("access_token")
        if not access_token:
            raise GitHubIntegrationError("GitHub did not return an access token.")
        profile = await self.fetch_profile(access_token)
        user = await self._resolve_oauth_user(state_record, profile, access_token)
        record = {
            "user_id": user.user_id,
            "github_id": profile.get("id"),
            "username": profile.get("login") or "",
            "avatar_url": profile.get("avatar_url") or "",
            "profile_url": profile.get("html_url") or "",
            "access_token_encrypted": _encrypt_token(access_token),
            "connected_at": _now().isoformat(),
        }
        self._connections[user.user_id] = record
        collection = self._connections_collection()
        if collection is not None:
            collection.replace_one({"user_id": user.user_id}, record, upsert=True)
        self._delete_state(state)
        await self.refresh_repositories(user.user_id)
        return user, create_access_token(user)

    async def _exchange_code(self, code: str) -> dict[str, Any]:
        data = {
            "client_id": GITHUB_CLIENT_ID,
            "client_secret": GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GITHUB_OAUTH_REDIRECT_URI,
        }
        return await self._to_thread(_json_request, "https://github.com/login/oauth/access_token", method="POST", data=data)

    async def fetch_profile(self, token: str) -> dict[str, Any]:
        return await self._to_thread(_json_request, f"{GITHUB_API}/user", token=token)

    async def fetch_emails(self, token: str) -> list[dict[str, Any]]:
        payload = await self._to_thread(_json_request, f"{GITHUB_API}/user/emails", token=token)
        return payload if isinstance(payload, list) else []

    async def _resolve_oauth_user(self, state_record: dict[str, Any], profile: dict[str, Any], access_token: str) -> User:
        user_id = state_record.get("user_id")
        if user_id:
            return user_repository.get_by_id(user_id)

        username = profile.get("login") or "github-user"
        github_id = str(profile.get("id") or username)
        email = profile.get("email") or ""
        if not email:
            emails = await self.fetch_emails(access_token)
            primary = next((item for item in emails if item.get("primary") and item.get("verified")), None)
            email = (primary or {}).get("email") or f"{username}@users.noreply.github.com"
        return user_repository.upsert_external_user("github", github_id, username, email)

    async def refresh_repositories(self, user_id: str) -> list[dict[str, Any]]:
        token = self.get_token(user_id)
        repos: list[dict[str, Any]] = []
        page = 1
        while page <= 4:
            query = urllib.parse.urlencode({"affiliation": "owner,collaborator,organization_member", "sort": "updated", "per_page": 100, "page": page})
            payload = await self._to_thread(_json_request, f"{GITHUB_API}/user/repos?{query}", token=token)
            if not isinstance(payload, list) or not payload:
                break
            repos.extend(payload)
            if len(payload) < 100:
                break
            page += 1
        for repo in repos:
            self._save_repo(user_id, repo)
        return repos

    async def workspace(self, user_id: str, refresh: bool = False) -> WorkspaceOverview:
        if refresh and self.is_connected(user_id):
            await self.refresh_repositories(user_id)
        repos = [self._to_workspace_repo(user_id, repo) for repo in self._load_repos(user_id)]
        analytics = self._analytics(repos)
        return WorkspaceOverview(connection=self.status(user_id), analytics=analytics, repositories=repos)

    def status(self, user_id: str) -> GitHubConnectionStatus:
        record = self._load_connection(user_id)
        if not record:
            return GitHubConnectionStatus(connected=False, configured=self.configured())
        return GitHubConnectionStatus(
            connected=True,
            configured=self.configured(),
            username=record.get("username", ""),
            avatar_url=record.get("avatar_url", ""),
            profile_url=record.get("profile_url", ""),
            connected_at=_parse_datetime(record.get("connected_at")),
        )

    def is_connected(self, user_id: str) -> bool:
        return self._load_connection(user_id) is not None

    def disconnect(self, user_id: str) -> None:
        self._connections.pop(user_id, None)
        collection = self._connections_collection()
        if collection is not None:
            collection.delete_many({"user_id": user_id})

    def launch_scan(self, user_id: str, repo_id: str, preset: ScanPreset) -> ScanApiResponse:
        repo = self._find_repo(user_id, repo_id)
        token = self.get_token(user_id)
        clone_url = _authenticated_clone_url(repo["html_url"], token) if repo.get("private") else None
        return scan_job_service.submit_scan(repo["html_url"], user_id, preset, clone_url=clone_url)

    def get_token(self, user_id: str) -> str:
        record = self._load_connection(user_id)
        if not record:
            raise GitHubIntegrationError("Connect GitHub before using the repository workspace.")
        return _decrypt_token(record["access_token_encrypted"])

    def _save_repo(self, user_id: str, repo: dict[str, Any]) -> None:
        record = {
            "user_id": user_id,
            "id": _repo_id(repo["full_name"]),
            "github_id": repo.get("id"),
            "full_name": repo.get("full_name"),
            "name": repo.get("name"),
            "owner": (repo.get("owner") or {}).get("login", ""),
            "description": repo.get("description") or "",
            "html_url": repo.get("html_url"),
            "clone_url": repo.get("clone_url"),
            "private": bool(repo.get("private")),
            "visibility": repo.get("visibility") or ("private" if repo.get("private") else "public"),
            "primary_language": repo.get("language") or "",
            "stars": repo.get("stargazers_count") or 0,
            "updated_at": repo.get("updated_at"),
            "topics": repo.get("topics") or [],
            "raw": repo,
            "synced_at": _now().isoformat(),
        }
        self._repos[user_id][record["id"]] = record
        collection = self._repos_collection()
        if collection is not None:
            collection.replace_one({"user_id": user_id, "id": record["id"]}, record, upsert=True)

    def _load_connection(self, user_id: str) -> dict[str, Any] | None:
        if user_id in self._connections:
            return self._connections[user_id]
        collection = self._connections_collection()
        if collection is not None:
            record = collection.find_one({"user_id": user_id})
            if record:
                record.pop("_id", None)
                self._connections[user_id] = record
                return record
        return None

    def _load_state(self, state: str) -> dict[str, Any]:
        if state in self._states:
            return self._states[state]
        collection = self._states_collection()
        if collection is not None:
            record = collection.find_one({"state": state})
            if record:
                record.pop("_id", None)
                self._states[state] = record
                return record
        raise GitHubIntegrationError("GitHub OAuth state is invalid or expired.")

    def _delete_state(self, state: str) -> None:
        self._states.pop(state, None)
        collection = self._states_collection()
        if collection is not None:
            collection.delete_many({"state": state})

    def _load_repos(self, user_id: str) -> list[dict[str, Any]]:
        collection = self._repos_collection()
        if collection is not None:
            values = []
            for item in collection.find({"user_id": user_id}):
                item.pop("_id", None)
                values.append(item)
            if values:
                self._repos[user_id] = {item["id"]: item for item in values}
                return sorted(values, key=lambda item: item.get("updated_at") or "", reverse=True)
        return sorted(self._repos[user_id].values(), key=lambda item: item.get("updated_at") or "", reverse=True)

    def _find_repo(self, user_id: str, repo_id: str) -> dict[str, Any]:
        for repo in self._load_repos(user_id):
            if repo["id"] == repo_id:
                return repo
        full_name = _full_name_from_id(repo_id)
        for repo in self._load_repos(user_id):
            if repo["full_name"] == full_name:
                return repo
        raise GitHubIntegrationError("Repository is not available in this workspace.")

    def _to_workspace_repo(self, user_id: str, repo: dict[str, Any]) -> WorkspaceRepository:
        scans = [scan_repository.get_scan(item.scan_id, user_id) for item in scan_repository.list_scans(user_id) if item.repo == repo["html_url"]]
        findings = [finding for scan in scans for finding in scan.vulnerabilities]
        severities = Counter(finding.severity.value for finding in findings)
        latest = scans[0] if scans else None
        summary, profile, attack_surface_score, security_posture = _profile_repository(repo, scans, len(findings), severities.get("Critical", 0), severities.get("High", 0))
        return WorkspaceRepository(
            id=repo["id"],
            github_id=int(repo.get("github_id") or 0),
            full_name=repo["full_name"],
            name=repo["name"],
            owner=repo["owner"],
            description=repo.get("description", ""),
            html_url=repo["html_url"],
            clone_url=repo.get("clone_url") or repo["html_url"],
            private=bool(repo.get("private")),
            visibility=repo.get("visibility") or ("private" if repo.get("private") else "public"),
            primary_language=repo.get("primary_language") or "",
            stars=int(repo.get("stars") or 0),
            updated_at=_parse_datetime(repo.get("updated_at")),
            topics=repo.get("topics") or [],
            scan_count=len(scans),
            findings_count=len(findings),
            critical_count=severities.get("Critical", 0),
            high_count=severities.get("High", 0),
            attack_surface_score=attack_surface_score,
            security_posture=security_posture,
            latest_scan_id=latest.scan_id if latest else "",
            latest_scan_status=latest.status if latest else "",
            ai_summary=summary,
            profile=profile,
        )

    def _analytics(self, repos: list[WorkspaceRepository]) -> WorkspaceAnalytics:
        if not repos:
            return WorkspaceAnalytics()
        scanned = [repo for repo in repos if repo.scan_count]
        risky = [repo for repo in repos if repo.critical_count or repo.high_count or repo.security_posture < 55]
        most_vulnerable = max(repos, key=lambda repo: repo.findings_count, default=None)
        return WorkspaceAnalytics(
            total_connected_repos=len(repos),
            repos_scanned=len(scanned),
            risky_repos=len(risky),
            average_posture=round(sum(repo.security_posture for repo in repos) / len(repos)),
            scan_coverage=round((len(scanned) / len(repos)) * 100),
            most_vulnerable_repo=most_vulnerable.full_name if most_vulnerable and most_vulnerable.findings_count else "",
        )

    async def _to_thread(self, func, *args, **kwargs):
        import asyncio

        return await asyncio.to_thread(func, *args, **kwargs)


github_workspace_service = GitHubWorkspaceService()
