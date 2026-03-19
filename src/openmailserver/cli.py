from __future__ import annotations

import json
from pathlib import Path

import typer

from openmailserver.config import Settings, get_settings
from openmailserver.database import SessionLocal, create_all
from openmailserver.platform.detect import current_platform
from openmailserver.schemas import DomainAttachRequest, DomainVerifyRequest, MailboxCreate
from openmailserver.services.backup_service import create_backup, restore_backup, validate_backup
from openmailserver.services.debug_service import doctor_report
from openmailserver.services.dns_service import build_dns_plan
from openmailserver.services.domain_service import (
    DomainError,
    attach_domain,
    bootstrap_primary_domain,
    get_domain_status,
    list_domains,
    verify_domain,
)
from openmailserver.services.installer import INSTALLER_PHASES, run_install
from openmailserver.services.mailbox_service import MailboxExistsError, provision_mailbox
from openmailserver.services.maildir_service import ensure_maildir

app = typer.Typer(help="Agent-friendly control plane for openmailserver.")
domains_app = typer.Typer(help="Manage attached and verified domains.")
app.add_typer(domains_app, name="domains")


def _session():
    return SessionLocal()


def _repo_root() -> Path:
    return Path.cwd()


def _env_path() -> Path:
    return _repo_root() / ".env"


@app.command()
def preflight() -> None:
    """Run platform-aware prerequisite checks."""
    report = doctor_report()
    typer.echo(json.dumps(report, indent=2))


@app.command()
def install(
    resume: bool = typer.Option(False, help="Resume from the saved installer state."),
    generate_only: bool = typer.Option(
        False,
        help="Only generate local config, runtime files, and service definitions.",
    ),
    completed_phase: str | None = typer.Option(
        None,
        "--completed-phase",
        help="Internal: mark a handoff phase as complete before resuming.",
    ),
) -> None:
    """Run the agent-first install flow with resume-aware orchestration."""
    settings = get_settings()
    adapter = current_platform()
    if completed_phase and completed_phase not in INSTALLER_PHASES:
        raise typer.BadParameter(f"Unknown phase: {completed_phase}")

    result = run_install(
        settings,
        adapter,
        _repo_root(),
        resume=resume,
        generate_only=generate_only,
        completed_phase=completed_phase,
    )
    typer.echo(json.dumps(result, indent=2))
    if result["status"] == "failed":
        raise typer.Exit(1)


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
        bootstrap_primary_domain(session)
        result = provision_mailbox(session, payload)
    except (MailboxExistsError, DomainError) as exc:
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
    """Convenience wrapper for the full install flow."""
    install()


@domains_app.command("list")
def domains_list() -> None:
    """List attached domains and their readiness state."""
    create_all()
    session = _session()
    try:
        bootstrap_primary_domain(session)
        items = [item.model_dump(mode="json") for item in list_domains(session)]
        typer.echo(json.dumps({"items": items}, indent=2))
    finally:
        session.close()


@domains_app.command("attach")
def domains_attach(
    name: str,
    dns_mode: str = typer.Option("external", help="Use 'external' today; 'managed' is reserved for future hosted flows"),
    registrar: str | None = typer.Option(None, help="Registrar or provider label"),
    external_domain_id: str | None = typer.Option(None, help="Provider-side domain identifier"),
    attach_source: str = typer.Option("manual", help="How this domain was attached"),
    auto_verify: bool = typer.Option(False, help="Mark the domain verified immediately"),
) -> None:
    """Attach a domain to this instance."""
    create_all()
    session = _session()
    try:
        result = attach_domain(
            session,
            DomainAttachRequest(
                name=name,
                dns_mode=dns_mode,
                registrar=registrar,
                external_domain_id=external_domain_id,
                attach_source=attach_source,
                auto_verify=auto_verify,
            ),
        )
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    except DomainError as exc:
        raise typer.BadParameter(str(exc)) from exc
    finally:
        session.close()


@domains_app.command("status")
def domains_status(name: str) -> None:
    """Show DNS plan and readiness state for a domain."""
    create_all()
    session = _session()
    try:
        bootstrap_primary_domain(session)
        typer.echo(json.dumps(get_domain_status(session, name).model_dump(mode="json"), indent=2))
    except DomainError as exc:
        raise typer.BadParameter(str(exc)) from exc
    finally:
        session.close()


@domains_app.command("verify")
def domains_verify(
    name: str,
    confirm_records: bool = typer.Option(
        False, help="Confirm that external DNS records have been applied"
    ),
    notes: str | None = typer.Option(None, help="Optional operator notes"),
) -> None:
    """Verify a domain so it can be used for mailbox creation."""
    create_all()
    session = _session()
    try:
        result = verify_domain(
            session,
            name,
            DomainVerifyRequest(confirmed_records=confirm_records, notes=notes),
        )
        typer.echo(json.dumps(result.model_dump(mode="json"), indent=2))
    except DomainError as exc:
        raise typer.BadParameter(str(exc)) from exc
    finally:
        session.close()


if __name__ == "__main__":
    app()
