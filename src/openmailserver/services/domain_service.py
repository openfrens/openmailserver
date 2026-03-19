from __future__ import annotations

from sqlalchemy.orm import Session

from openmailserver.config import get_settings
from openmailserver.models import Domain, utcnow
from openmailserver.schemas import DomainAttachRequest, DomainRead, DomainStatusResponse, DomainVerifyRequest
from openmailserver.services.dns_service import build_dns_plan

READY_VERIFICATION_STATUSES = {"verified"}


class DomainError(ValueError):
    pass


class DomainNotFoundError(DomainError):
    pass


class DomainNotReadyError(DomainError):
    pass


def _normalize_domain_name(name: str) -> str:
    value = name.strip().lower().rstrip(".")
    if not value:
        raise DomainError("Domain name is required")
    return value


def _mailbox_ready(domain: Domain) -> bool:
    return domain.verification_status in READY_VERIFICATION_STATUSES


def _domain_read(domain: Domain) -> DomainRead:
    return DomainRead(
        id=domain.id,
        name=domain.name,
        registrar=domain.registrar,
        external_domain_id=domain.external_domain_id,
        verification_status=domain.verification_status,
        dns_mode=domain.dns_mode,
        nameserver_mode=domain.nameserver_mode,
        attach_source=domain.attach_source,
        mailbox_ready=_mailbox_ready(domain),
        last_error=domain.last_error,
        metadata=domain.metadata_json or {},
        attached_at=domain.attached_at,
        verified_at=domain.verified_at,
        last_checked_at=domain.last_checked_at,
        created_at=domain.created_at,
    )


def _mark_verified(domain: Domain, reason: str | None = None) -> None:
    now = utcnow()
    domain.verification_status = "verified"
    domain.last_checked_at = now
    domain.verified_at = now
    domain.last_error = None
    if reason:
        metadata = dict(domain.metadata_json or {})
        metadata["verification_reason"] = reason
        domain.metadata_json = metadata


def _build_verification_summary(domain: Domain) -> dict:
    return {
        "ready_for_mailboxes": _mailbox_ready(domain),
        "dns_mode": domain.dns_mode,
        "verification_status": domain.verification_status,
        "requires_manual_confirmation": domain.dns_mode == "external"
        and domain.name != get_settings().primary_domain,
        "last_error": domain.last_error,
    }


def _status_response(domain: Domain) -> DomainStatusResponse:
    return DomainStatusResponse(
        domain=_domain_read(domain),
        dns_plan=build_dns_plan(domain.name),
        verification=_build_verification_summary(domain),
    )


def get_domain(db: Session, name: str) -> Domain:
    domain = db.query(Domain).filter(Domain.name == _normalize_domain_name(name)).first()
    if not domain:
        raise DomainNotFoundError("Domain is not attached")
    return domain


def list_domains(db: Session) -> list[DomainStatusResponse]:
    domains = db.query(Domain).order_by(Domain.name.asc()).all()
    return [_status_response(domain) for domain in domains]


def bootstrap_primary_domain(db: Session) -> Domain:
    settings = get_settings()
    domain_name = _normalize_domain_name(settings.primary_domain)
    domain = db.query(Domain).filter(Domain.name == domain_name).first()
    if domain:
        changed = False
        if domain.attach_source == "manual":
            domain.attach_source = "local-config"
            changed = True
        if not domain.attached_at:
            domain.attached_at = utcnow()
            changed = True
        if domain.verification_status != "verified":
            _mark_verified(domain, "Primary domain is configured on this instance")
            changed = True
        if changed:
            db.commit()
            db.refresh(domain)
        return domain

    domain = Domain(
        name=domain_name,
        verification_status="verified",
        dns_mode="external",
        nameserver_mode="external",
        attach_source="local-config",
        metadata_json={"bootstrap": "primary-domain"},
        attached_at=utcnow(),
        verified_at=utcnow(),
        last_checked_at=utcnow(),
    )
    db.add(domain)
    db.commit()
    db.refresh(domain)
    return domain


def attach_domain(db: Session, payload: DomainAttachRequest) -> DomainStatusResponse:
    settings = get_settings()
    name = _normalize_domain_name(payload.name)
    domain = db.query(Domain).filter(Domain.name == name).first()
    is_new = domain is None
    if domain is None:
        domain = Domain(name=name)
        db.add(domain)

    nameserver_mode = payload.nameserver_mode or (
        "managed" if payload.dns_mode == "managed" else "external"
    )

    domain.registrar = payload.registrar
    domain.external_domain_id = payload.external_domain_id
    domain.dns_mode = payload.dns_mode
    domain.nameserver_mode = nameserver_mode
    domain.attach_source = payload.attach_source
    domain.metadata_json = dict(payload.metadata or {})
    domain.attached_at = domain.attached_at or utcnow()
    domain.last_error = None

    if payload.auto_verify or (name == settings.primary_domain and payload.dns_mode == "external"):
        _mark_verified(domain, "Primary domain is configured on this instance")
    elif is_new or domain.verification_status == "verified":
        domain.verification_status = "unverified"
        domain.verified_at = None

    db.commit()
    db.refresh(domain)
    return _status_response(domain)


def verify_domain(db: Session, name: str, payload: DomainVerifyRequest) -> DomainStatusResponse:
    domain = get_domain(db, name)

    if domain.name == get_settings().primary_domain:
        _mark_verified(domain, "Primary domain is configured on this instance")
    elif payload.confirmed_records:
        _mark_verified(domain, "Operator confirmed external DNS records")
    else:
        domain.verification_status = "pending"
        domain.last_checked_at = utcnow()
        domain.last_error = "DNS records still need to be confirmed for this domain"
        if payload.notes:
            metadata = dict(domain.metadata_json or {})
            metadata["verification_notes"] = payload.notes
            domain.metadata_json = metadata

    db.commit()
    db.refresh(domain)
    return _status_response(domain)


def get_domain_status(db: Session, name: str) -> DomainStatusResponse:
    return _status_response(get_domain(db, name))


def ensure_domain_ready(db: Session, name: str) -> Domain:
    domain = get_domain(db, name)
    if not _mailbox_ready(domain):
        raise DomainNotReadyError(
            "Domain is not ready. Attach and verify the domain before creating mailboxes."
        )
    return domain
