from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import typer
from cryptography.fernet import Fernet

from openmailserver.config import Settings, get_settings
from openmailserver.database import SessionLocal, create_all
from openmailserver.models import ApiKey
from openmailserver.schemas import MailboxCreate
from openmailserver.security import DEFAULT_ADMIN_SCOPES, generate_api_key
from openmailserver.services.backup_service import create_backup, restore_backup, validate_backup
from openmailserver.services.debug_service import doctor_report
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.mailbox_service import (
    MailboxExistsError,
    MailboxNotFoundError,
    provision_mailbox,
    set_mailbox_password,
)
from openmailserver.services.maildir_service import ensure_maildir
from openmailserver.services.mox_service import MoxSyncError, MoxSyncService
from openmailserver.services.runtime_setup import render_runtime_bundle

app = typer.Typer(help="Agent-friendly control plane for openmailserver.")


def _session():
    return SessionLocal()


def _repo_root() -> Path:
    return Path.cwd()


def _env_path() -> Path:
    return _repo_root() / ".env"


def _compose_available() -> bool:
    return shutil.which("docker") is not None and (_repo_root() / "compose.yaml").exists()


def _delegate_to_api_container(args: list[str]) -> None:
    result = subprocess.run(
        ["docker", "compose", "exec", "-T", "api", "openmailserver", *args],
        cwd=_repo_root(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout:
        typer.echo(result.stdout.rstrip())
    if result.returncode != 0:
        typer.echo((result.stderr or result.stdout).strip(), err=True)
        raise typer.Exit(code=result.returncode)


def _write_env(settings: Settings, admin_key: str, backup_key: str) -> Path:
    path = _env_path()
    content = f"""OPENMAILSERVER_ENV=development
OPENMAILSERVER_HOST={settings.host}
OPENMAILSERVER_PORT={settings.port}
OPENMAILSERVER_API_BIND={settings.api_bind}
OPENMAILSERVER_MOX_HTTP_BIND={settings.mox_http_bind}
OPENMAILSERVER_MOX_HTTPS_BIND={settings.mox_https_bind}
OPENMAILSERVER_DATA_DIR={settings.data_dir}
OPENMAILSERVER_LOG_DIR={settings.log_dir}
OPENMAILSERVER_DATABASE_URL={settings.database_url}
OPENMAILSERVER_FALLBACK_DATABASE_URL={settings.fallback_database_url}
OPENMAILSERVER_DATABASE_SUPERUSER={settings.database_superuser}
OPENMAILSERVER_DATABASE_SUPERUSER_PASSWORD={settings.database_superuser_password or ""}
OPENMAILSERVER_MAILDIR_ROOT={settings.maildir_root}
OPENMAILSERVER_ATTACHMENT_ROOT={settings.attachment_root}
OPENMAILSERVER_CONFIG_ROOT={settings.config_root}
OPENMAILSERVER_SMTP_HOST={settings.canonical_hostname}
OPENMAILSERVER_SMTP_PORT=465
OPENMAILSERVER_SMTP_SECURITY=ssl
OPENMAILSERVER_SMTP_VERIFY_TLS={str(settings.smtp_verify_tls).lower()}
OPENMAILSERVER_SMTP_TIMEOUT_SECONDS={settings.smtp_timeout_seconds}
OPENMAILSERVER_IMAP_HOST={settings.effective_imap_host}
OPENMAILSERVER_IMAP_PORT={settings.imap_port}
OPENMAILSERVER_IMAP_SECURITY={settings.imap_security}
OPENMAILSERVER_IMAP_VERIFY_TLS={str(settings.imap_verify_tls).lower()}
OPENMAILSERVER_IMAP_TIMEOUT_SECONDS={settings.imap_timeout_seconds}
OPENMAILSERVER_TRANSPORT_MODE={settings.transport_mode}
OPENMAILSERVER_CANONICAL_HOSTNAME={settings.canonical_hostname}
OPENMAILSERVER_PRIMARY_DOMAIN={settings.primary_domain}
OPENMAILSERVER_PUBLIC_IP={settings.public_ip}
OPENMAILSERVER_MOX_IMAGE={settings.mox_image}
OPENMAILSERVER_MOX_BINARY={settings.mox_binary}
OPENMAILSERVER_MOX_ADMIN_ACCOUNT={settings.mox_admin_account}
OPENMAILSERVER_MOX_ADMIN_ADDRESS={settings.effective_mox_admin_address}
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


def _install_settings_with_overrides(
    settings: Settings,
    *,
    api_bind: str | None = None,
    mox_http_bind: str | None = None,
    mox_https_bind: str | None = None,
) -> Settings:
    updates = {
        key: value
        for key, value in {
            "api_bind": api_bind,
            "mox_http_bind": mox_http_bind,
            "mox_https_bind": mox_https_bind,
        }.items()
        if value is not None
    }
    return settings.model_copy(update=updates) if updates else settings


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
    """Run prerequisite checks for the containerized runtime."""
    report = doctor_report()
    typer.echo(json.dumps(report, indent=2))


def _run_install(
    *,
    api_bind: str | None = None,
    mox_http_bind: str | None = None,
    mox_https_bind: str | None = None,
) -> None:
    settings = _install_settings_with_overrides(
        get_settings(),
        api_bind=api_bind,
        mox_http_bind=mox_http_bind,
        mox_https_bind=mox_https_bind,
    )
    settings.ensure_directories()
    create_all()
    admin_key = settings.admin_api_key or _bootstrap_admin_key()
    backup_key = settings.backup_encryption_key or Fernet.generate_key().decode("utf-8")
    env_path = _write_env(settings, admin_key, backup_key)
    runtime_files = render_runtime_bundle(settings, _repo_root())
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "runtime": "container-mox",
                "env_file": str(env_path),
                "published_ports": {
                    "api": settings.api_bind,
                    "mox_http": settings.mox_http_bind,
                    "mox_https": settings.mox_https_bind,
                },
                "runtime_files": runtime_files,
                "quickstart_command": runtime_files["quickstart_command"],
                "next_steps": [
                    runtime_files["quickstart_command"],
                    "docker compose up -d",
                    "docker compose ps",
                    "openmailserver doctor",
                ],
                "admin_api_key": admin_key,
            },
            indent=2,
        )
    )


@app.command()
def install(
    api_bind: str | None = typer.Option(
        None,
        help="Docker host bind for the API service, for example 8787 or 127.0.0.1:8787.",
    ),
    mox_http_bind: str | None = typer.Option(
        None,
        help="Docker host bind for mox HTTP, for example 80 or 127.0.0.1:8080.",
    ),
    mox_https_bind: str | None = typer.Option(
        None,
        help="Docker host bind for mox HTTPS, for example 443 or 127.0.0.1:8443.",
    ),
) -> None:
    """Generate local config, container runtime directories, and install metadata."""
    _run_install(
        api_bind=api_bind,
        mox_http_bind=mox_http_bind,
        mox_https_bind=mox_https_bind,
    )


@app.command("mox-quickstart")
def mox_quickstart() -> None:
    """Generate container-safe mox config for the current domain settings."""
    settings = get_settings()
    try:
        result = MoxSyncService(settings).quickstart_runtime()
    except MoxSyncError as exc:
        raise typer.BadParameter(str(exc)) from exc
    typer.echo(
        json.dumps(
            {
                "status": "ok",
                "runtime": "container-mox",
                "canonical_hostname": settings.canonical_hostname,
                "admin_address": settings.effective_mox_admin_address,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
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
    settings = get_settings()
    if settings.database_host == "postgres" and _compose_available():
        args = ["create-mailbox", local_part, domain]
        if password:
            args.extend(["--password", password])
        _delegate_to_api_container(args)
        return

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


@app.command("set-mailbox-password")
def set_mailbox_password_command(email: str, password: str | None = None) -> None:
    """Rotate a mailbox password for IMAP and SMTP submission."""
    settings = get_settings()
    if settings.database_host == "postgres" and _compose_available():
        args = ["set-mailbox-password", email]
        if password:
            args.extend(["--password", password])
        _delegate_to_api_container(args)
        return

    create_all()
    session = _session()
    new_password = password or generate_api_key(prefix="mailpass").raw_key
    try:
        result = set_mailbox_password(session, email, new_password)
    except MailboxNotFoundError as exc:
        raise typer.BadParameter(str(exc)) from exc
    finally:
        session.close()
    typer.echo(
        json.dumps(
            {
                "mailbox": result.mailbox.model_dump(),
                "password": result.password,
            },
            indent=2,
        )
    )


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
            json.dumps(
                {"items": [entry.model_dump(mode="json") for entry in list_queue(session)]},
                indent=2,
            )
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
            typer.echo(
                json.dumps(
                    {"status": "missing", "reason": "No backup archive found"},
                    indent=2,
                )
            )
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
    _run_install()
    doctor()


if __name__ == "__main__":
    app()
