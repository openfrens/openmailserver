from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from collections.abc import Iterable
from dataclasses import dataclass

import bcrypt

ADMIN_SCOPE = "admin"
DEBUG_READ_SCOPE = "debug:read"
MAIL_READ_SCOPE = "mail:read"
MAIL_SEND_SCOPE = "mail:send"
WILDCARD_SCOPE = "*"

DEFAULT_ADMIN_SCOPES = (ADMIN_SCOPE, DEBUG_READ_SCOPE, MAIL_READ_SCOPE, MAIL_SEND_SCOPE)
DEFAULT_MAILBOX_SCOPES = (MAIL_READ_SCOPE, MAIL_SEND_SCOPE)

SECRET_REPLACEMENTS = [
    re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*([^\s]+)"),
    re.compile(r"(?i)(authorization:\s*bearer\s+)([a-z0-9._-]+)"),
]


def generate_secret(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    return hmac.compare_digest(hash_api_key(raw_key), hashed_key)


def hash_mailbox_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")
    return "{BLF-CRYPT}" + hashed


def verify_mailbox_password(password: str, password_hash: str) -> bool:
    normalized = password_hash.removeprefix("{BLF-CRYPT}")
    return bcrypt.checkpw(password.encode("utf-8"), normalized.encode("utf-8"))


def redact_value(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 6:
        return "***"
    return f"{value[:3]}***{value[-3:]}"


def redact_text(text: str) -> str:
    redacted = text
    for pattern in SECRET_REPLACEMENTS:
        redacted = pattern.sub(lambda match: f"{match.group(1)}***REDACTED***", redacted)
    return redacted


def parse_scopes(scopes: str | Iterable[str]) -> list[str]:
    if isinstance(scopes, str):
        values = [scope.strip() for scope in scopes.split(",")]
    else:
        values = [scope.strip() for scope in scopes]
    return sorted({scope for scope in values if scope})


def scopes_include(required: str, granted_scopes: Iterable[str]) -> bool:
    granted = set(granted_scopes)
    return required in granted or WILDCARD_SCOPE in granted or ADMIN_SCOPE in granted


@dataclass(slots=True)
class GeneratedApiKey:
    raw_key: str
    hashed_key: str


def generate_api_key(prefix: str = "oms") -> GeneratedApiKey:
    raw = f"{prefix}_{generate_secret(24)}"
    return GeneratedApiKey(raw_key=raw, hashed_key=hash_api_key(raw))
