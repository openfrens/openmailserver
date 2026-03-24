from __future__ import annotations

import json

from cryptography.fernet import Fernet

from openmailserver.config import Settings, get_settings


def _fernet(settings: Settings) -> Fernet:
    key = settings.backup_encryption_key
    if not key:
        raise ValueError("OPENMAILSERVER_BACKUP_ENCRYPTION_KEY must be configured")
    return Fernet(key.encode("utf-8"))


def _load_payload(settings: Settings) -> dict:
    path = settings.runtime_secret_path
    if not path.exists():
        return {"mailbox_passwords": {}}
    decrypted = _fernet(settings).decrypt(path.read_bytes())
    payload = json.loads(decrypted.decode("utf-8"))
    payload.setdefault("mailbox_passwords", {})
    return payload


def _save_payload(settings: Settings, payload: dict) -> None:
    settings.runtime_secret_path.parent.mkdir(parents=True, exist_ok=True)
    encrypted = _fernet(settings).encrypt(json.dumps(payload, sort_keys=True).encode("utf-8"))
    settings.runtime_secret_path.write_bytes(encrypted)


def store_mailbox_password(address: str, password: str, settings: Settings | None = None) -> None:
    active_settings = settings or get_settings()
    payload = _load_payload(active_settings)
    payload["mailbox_passwords"][address] = password
    _save_payload(active_settings, payload)


def mailbox_password_for(address: str, settings: Settings | None = None) -> str | None:
    active_settings = settings or get_settings()
    payload = _load_payload(active_settings)
    return payload["mailbox_passwords"].get(address)
