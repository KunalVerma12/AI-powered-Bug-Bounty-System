from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

try:
    from backend.app.models.schemas import User
    from backend.app.services.database import get_collection
except ModuleNotFoundError:
    from app.models.schemas import User
    from app.services.database import get_collection


SECRET_KEY = os.environ.get("BUG_BOUNTY_AUTH_SECRET", "dev-bug-bounty-secret")
TOKEN_TTL_HOURS = 24


class AuthError(Exception):
    """Raised when authentication cannot be completed."""


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str, salt: str | None = None) -> str:
    salt_value = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_value.encode("utf-8"), 120000)
    return f"{salt_value}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, _hash = stored_hash.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored_hash)


def create_access_token(user: User) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user.user_id,
        "username": user.username,
        "email": user.email,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()),
    }
    header_segment = _b64encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{header_segment}.{payload_segment}.{_b64encode(signature)}"


def decode_access_token(token: str) -> User:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise AuthError("Invalid authentication token.") from exc

    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    expected_signature = hmac.new(SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(expected_signature, _b64decode(signature_segment)):
        raise AuthError("Authentication token signature is invalid.")

    payload = json.loads(_b64decode(payload_segment).decode("utf-8"))
    if int(payload.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
        raise AuthError("Authentication token has expired.")

    user_id = payload.get("sub")
    email = payload.get("email")
    username = payload.get("username") or email.split("@")[0] if email else None
    if not user_id or not email or not username:
        raise AuthError("Authentication token payload is incomplete.")
    return User(user_id=user_id, username=username, email=email)


class UserRepository:
    def __init__(self) -> None:
        self._users_by_email: dict[str, dict[str, str]] = {}

    def _users_collection(self):
        return get_collection("users")

    def _activity_collection(self):
        return get_collection("activity_events")

    def _log_activity(self, event_type: str, user_id: str, metadata: dict[str, str]) -> None:
        collection = self._activity_collection()
        if collection is None:
            return
        collection.insert_one(
            {
                "event_type": event_type,
                "user_id": user_id,
                "metadata": metadata,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    def register(self, username: str, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        collection = self._users_collection()
        if collection is not None:
            existing = collection.find_one({"email": normalized_email})
            if existing:
                raise AuthError("An account with this email already exists.")
        elif normalized_email in self._users_by_email:
            raise AuthError("An account with this email already exists.")
        record = {
            "user_id": str(uuid4()),
            "username": username.strip(),
            "email": normalized_email,
            "password_hash": hash_password(password),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if collection is not None:
            collection.insert_one(record)
        else:
            self._users_by_email[normalized_email] = record
        self._log_activity("user_registered", record["user_id"], {"email": normalized_email})
        return User(user_id=record["user_id"], username=record["username"], email=record["email"])

    def login(self, email: str, password: str) -> User:
        normalized_email = email.strip().lower()
        collection = self._users_collection()
        if collection is not None:
            record = collection.find_one({"email": normalized_email})
        else:
            record = self._users_by_email.get(normalized_email)
        if not record or not verify_password(password, record["password_hash"]):
            raise AuthError("Invalid email or password.")
        self._log_activity("user_login", record["user_id"], {"email": normalized_email})
        return User(user_id=record["user_id"], username=record["username"], email=record["email"])

    def get_by_id(self, user_id: str) -> User:
        collection = self._users_collection()
        if collection is not None:
            record = collection.find_one({"user_id": user_id})
            if record:
                return User(user_id=record["user_id"], username=record["username"], email=record["email"])
        for record in self._users_by_email.values():
            if record["user_id"] == user_id:
                return User(user_id=record["user_id"], username=record["username"], email=record["email"])
        raise AuthError("User account no longer exists.")

    def upsert_external_user(self, provider: str, provider_id: str, username: str, email: str) -> User:
        normalized_email = email.strip().lower()
        collection = self._users_collection()
        if collection is not None:
            record = collection.find_one({"external_provider": provider, "external_id": provider_id}) or collection.find_one({"email": normalized_email})
            if record:
                updates = {
                    "username": username.strip() or record.get("username") or normalized_email.split("@", 1)[0],
                    "email": normalized_email,
                    "external_provider": provider,
                    "external_id": provider_id,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
                collection.update_one({"user_id": record["user_id"]}, {"$set": updates})
                return User(user_id=record["user_id"], username=updates["username"], email=updates["email"])
        else:
            for record in self._users_by_email.values():
                if record.get("external_provider") == provider and record.get("external_id") == provider_id:
                    record.update({"username": username.strip() or record["username"], "email": normalized_email})
                    return User(user_id=record["user_id"], username=record["username"], email=record["email"])
            if normalized_email in self._users_by_email:
                record = self._users_by_email[normalized_email]
                record.update({"external_provider": provider, "external_id": provider_id, "username": username.strip() or record["username"]})
                return User(user_id=record["user_id"], username=record["username"], email=record["email"])

        record = {
            "user_id": str(uuid4()),
            "username": username.strip() or normalized_email.split("@", 1)[0],
            "email": normalized_email,
            "password_hash": "",
            "external_provider": provider,
            "external_id": provider_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if collection is not None:
            collection.insert_one(record)
        else:
            self._users_by_email[normalized_email] = record
        self._log_activity("external_user_authenticated", record["user_id"], {"provider": provider, "email": normalized_email})
        return User(user_id=record["user_id"], username=record["username"], email=record["email"])

    def clear_for_tests(self) -> None:
        self._users_by_email.clear()
        collection = self._users_collection()
        if collection is not None:
            collection.delete_many({})
        activity = self._activity_collection()
        if activity is not None:
            activity.delete_many({})


user_repository = UserRepository()
