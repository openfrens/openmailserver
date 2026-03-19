from __future__ import annotations

from openmailserver.models import Domain
from openmailserver.schemas import DomainAttachRequest, DomainVerifyRequest
from openmailserver.services.domain_service import (
    DomainNotFoundError,
    DomainNotReadyError,
    attach_domain,
    bootstrap_primary_domain,
    ensure_domain_ready,
    get_domain_status,
    verify_domain,
)


def test_bootstrap_primary_domain_creates_ready_domain(db_session):
    domain = bootstrap_primary_domain(db_session)

    assert domain.name == "example.test"
    assert domain.verification_status == "verified"
    assert domain.attach_source == "local-config"


def test_attach_domain_marks_domain_ready_when_auto_verified(db_session):
    response = attach_domain(
        db_session,
        DomainAttachRequest(
            name="owned.test",
            dns_mode="external",
            attach_source="manual",
            auto_verify=True,
        ),
    )

    assert response.domain.name == "owned.test"
    assert response.domain.mailbox_ready is True


def test_verify_external_domain_requires_confirmation(db_session):
    attach_domain(db_session, DomainAttachRequest(name="external.test", dns_mode="external"))

    pending = verify_domain(db_session, "external.test", DomainVerifyRequest())
    verified = verify_domain(
        db_session,
        "external.test",
        DomainVerifyRequest(confirmed_records=True, notes="records applied"),
    )

    assert pending.domain.verification_status == "pending"
    assert verified.domain.verification_status == "verified"
    assert verified.domain.mailbox_ready is True


def test_get_domain_status_rejects_missing_domain(db_session):
    try:
        get_domain_status(db_session, "missing.test")
    except DomainNotFoundError:
        return

    raise AssertionError("Expected missing domain lookup to fail")


def test_ensure_domain_ready_requires_verified_status(db_session):
    db_session.add(
        Domain(
            name="pending.test",
            verification_status="pending",
            dns_mode="external",
            nameserver_mode="external",
            attach_source="manual",
        )
    )
    db_session.commit()

    try:
        ensure_domain_ready(db_session, "pending.test")
    except DomainNotReadyError as exc:
        assert "Attach and verify the domain" in str(exc)
        return

    raise AssertionError("Expected unready domain to be rejected")
