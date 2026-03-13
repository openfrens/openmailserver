from __future__ import annotations

import json
from pathlib import Path

import typer
from cryptography.fernet import Fernet

from openmailserver.config import Settings, get_settings
from openmailserver.database import SessionLocal, create_all
from openmailserver.models import ApiKey
from openmailserver.platform.detect import current_platform
from openmailserver.schemas import MailboxCreate
from openmailserver.security import DEFAULT_ADMIN_SCOPES, generate_api_key
from openmailserver.services.backup_service import create_backup, restore_backup, validate_backup
from openmailserver.services.debug_service import doctor_report
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.mailbox_service import MailboxExistsError, provision_mailbox
from openmailserver.services.maildir_service import ensure_maildir
from openmailserver.services.runtime_setup import render_runtime_bundle

app = typer.Typer(help="Agent-friendly control plane for openmailserver.")


def _session():
    return SessionLocal()


def _repo_root() -> Path:
    return Path.cwd()


def _env_path() -> Path:
    return _repo_root() / ".env"


def _write_env(settings: Settings, admin_key: str, backup_key: str) -> Path:
    path = _env_path()
    content = f"""OPENMAILSERVER_ENV=development
OPENMAILSERVER_HOST={settings.host}
OPENMAILSERVER_PORT={settings.port}
OPENMAILSERVER_DATA_DIR={settings.data_dir}
OPENMAILSERVER_LOG_DIR={settings.log_dir}
OPENMAILSERVER_DATABASE_URL={settings.database_url}
OPENMAILSERVER_FALLBACK_DATABASE_URL={settings.fallback_database_url}
OPENMAILSERVER_DATABASE_SUPERUSER={settings.database_superuser}
OPENMAILSERVER_DATABASE_SUPERUSER_PASSWORD={settings.database_superuser_password or ""}
OPENMAILSERVER_MAILDIR_ROOT={settings.maildir_root}
OPENMAILSERVER_ATTACHMENT_ROOT={settings.attachment_root}
OPENMAILSERVER_CONFIG_ROOT={settings.config_root}
OPENMAILSERVER_SMTP_HOST={settings.smtp_host}
OPENMAILSERVER_SMTP_PORT={settings.smtp_port}
OPENMAILSERVER_SMTP_TIMEOUT_SECONDS={settings.smtp_timeout_seconds}
OPENMAILSERVER_TRANSPORT_MODE={settings.transport_mode}
OPENMAILSERVER_CANONICAL_HOSTNAME={settings.canonical_hostname}
OPENMAILSERVER_PRIMARY_DOMAIN={settings.primary_domain}
OPENMAILSERVER_PUBLIC_IP={settings.public_ip}
OPENMAILSERVER_API_KEY_HEADER={settings.api_key_header}
OPENMAILSERVER_LOG_FILE={settings.log_file}
OPENMAILSERVER_ADMIN_API_KEY={admin_key}
OPENMAILSERVER_BACKUP_ENCRYPTION_KEY={backup_key}
OPENMAILSERVER_MAX_SENDS_PER_HOUR={settings.max_sends_per_hour}
OPENMAILSERVER_MAX_MESSAGES_PER_MAILBOX={settings.max_messages_per_mailbox}
OPENMAILSERVER_MAX_ATTACHMENT_BYTES={settings.max_attachment_bytes}
OPENMAILSERVER_DEBUG_API_ENABLED={str(settings.debug_api_enabled).lower()}
"""
    path.write_text(content, encoding="utf-8")
    return path


def _bootstrap_admin_key() -> str:
    session = _session()
    key = generate_api_key(prefix="admin")
    session.add(
        ApiKey(
            name="installer-admin",
            key_hash=key.hashed_key,
            scopes=list(DEFAULT_ADMIN_SCOPES),
        )
    )
    session.commit()
    session.close()
    return key.raw_key


@app.command()
def preflight() -> None:
    """Run platform-aware prerequisite checks."""
    report = doctor_report()
    typer.echo(json.dumps(report, indent=2))


@app.command()
def install() -> None:
    """Generate local config, mail-stack files, secrets, and service definitions."""
    settings = get_settings()
    settings.ensure_directories()
    adapter = current_platform()
    create_all()
    admin_key = settings.admin_api_key or _bootstrap_admin_key()
    backup_key = settings.backup_encryption_key or Fernet.generate_key().decode("utf-8")
    env_path = _write_env(settings, admin_key, backup_key)
    service_definition = adapter.api_service_unit(_repo_root())
    service_name = (
        "openmailserver.service" if adapter.name == "linux" else "ai.openmailserver.api.plist"
    )
    service_file = settings.config_root / service_name
    service_file.write_text(service_definition, encoding="utf-8")
    runtime_files = render_runtime_bundle(settings, adapter, _repo_root())
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "platform": adapter.name,
                "env_file": str(env_path),
                "service_file": str(service_file),
                "install_hint": adapter.install_hint(),
                "service_hint": adapter.service_hint(),
                "runtime_files": runtime_files,
                "admin_api_key": admin_key,
            },
            indent=2,
        )
    )


@app.command("plan-dns")
def plan_dns() -> None:
    """Print the DNS records required for direct-to-MX setup."""
    settings = get_settings()
    typer.echo(
        json.dumps(
            {
                "hostname": settings.canonical_hostname,
                "domain": settings.primary_domain,
                "records": build_dns_plan(),
            },
            indent=2,
        )
    )


@app.command()
def doctor() -> None:
    """Run strict direct-delivery readiness checks."""
    typer.echo(json.dumps(doctor_report(), indent=2))


@app.command("create-mailbox")
def create_mailbox(local_part: str, domain: str, password: str | None = None) -> None:
    """Create a mailbox and return its credentials."""
    payload = MailboxCreate(local_part=local_part, domain=domain, password=password)
    create_all()
    session = _session()
    try:
        result = provision_mailbox(session, payload)
    except MailboxExistsError as exc:
        raise typer.BadParameter(str(exc)) from exc
    finally:
        session.close()
    typer.echo(json.dumps(result.model_dump(), indent=2))


@app.command("smoke-test")
def smoke_test() -> None:
    """Validate the first-send / first-receive flow using a local mailbox."""
    settings = get_settings()
    address = f"smoke@{settings.primary_domain}"
    ensure_maildir(address)
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "mailbox": address,
                "next": "Use the API to send a local test message.",
            },
            indent=2,
        )
    )


@app.command()
def queue() -> None:
    """Show current outbound queue state."""
    from openmailserver.services.queue_service import list_queue

    create_all()
    session = _session()
    try:
        typer.echo(
            json.dumps({"items": [entry.model_dump(mode="json") for entry in list_queue(session)]}, indent=2)
        )
    finally:
        session.close()


@app.command("backup-create")
def backup_create() -> None:
    """Create an encrypted backup archive."""
    create_all()
    session = _session()
    try:
        path = create_backup(session)
        typer.echo(json.dumps({"status": "ok", "path": str(path)}, indent=2))
    finally:
        session.close()


@app.command("backup-verify")
def backup_verify(path: str | None = None) -> None:
    """Verify a backup archive."""
    settings = get_settings()
    if path:
        backup_path = Path(path)
    else:
        backups = sorted(settings.backup_dir.glob("*.enc"))
        if not backups:
            typer.echo(json.dumps({"status": "missing", "reason": "No backup archive found"}, indent=2))
            raise typer.Exit(code=1)
        backup_path = backups[-1]
    typer.echo(json.dumps(validate_backup(backup_path), indent=2))


@app.command()
def restore(path: str) -> None:
    """Restore a backup archive into the local runtime."""
    create_all()
    session = _session()
    try:
        typer.echo(json.dumps(restore_backup(session, Path(path)), indent=2))
    finally:
        session.close()


@app.command()
def bootstrap() -> None:
    """Convenience wrapper for install -> doctor."""
    install()
    doctor()


if __name__ == "__main__":
    app()
