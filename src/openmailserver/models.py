from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from openmailserver.database import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


def json_type():
    return JSON().with_variant(JSONB, "postgresql")


class Domain(Base):
    __tablename__ = "domains"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    mailboxes: Mapped[list[Mailbox]] = relationship(back_populates="domain")


class Mailbox(Base):
    __tablename__ = "mailboxes"
    __table_args__ = (UniqueConstraint("local_part", "domain_id", name="uq_mailbox_local_domain"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    domain_id: Mapped[int] = mapped_column(ForeignKey("domains.id"), index=True)
    local_part: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    runtime_account: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    maildir_path: Mapped[str] = mapped_column(String(1024))
    quota: Mapped[int] = mapped_column(Integer, default=0)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    domain: Mapped[Domain] = relationship(back_populates="mailboxes")
    api_keys: Mapped[list[ApiKey]] = relationship(back_populates="mailbox")


class Alias(Base):
    __tablename__ = "aliases"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    destination: Mapped[str] = mapped_column(String(255), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    scopes: Mapped[list[str]] = mapped_column(json_type())
    mailbox_id: Mapped[int | None] = mapped_column(ForeignKey("mailboxes.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    mailbox: Mapped[Mailbox | None] = relationship(back_populates="api_keys")


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender: Mapped[str] = mapped_column(String(255), index=True)
    recipients: Mapped[list[str]] = mapped_column(json_type())
    cc: Mapped[list[str]] = mapped_column(json_type(), default=list)
    bcc: Mapped[list[str]] = mapped_column(json_type(), default=list)
    subject: Mapped[str] = mapped_column(String(998))
    text_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_mime: Mapped[str | None] = mapped_column(Text, nullable=True)
    message_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    queue_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    state: Mapped[str] = mapped_column(String(64), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    debug_metadata: Mapped[dict] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list[DeliveryEvent]] = relationship(back_populates="message")


class DeliveryEvent(Base):
    __tablename__ = "delivery_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    outbound_message_id: Mapped[int] = mapped_column(ForeignKey("outbound_messages.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    details: Mapped[dict] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    message: Mapped[OutboundMessage] = relationship(back_populates="events")


class TrustedPeer(Base):
    __tablename__ = "trusted_peers"

    id: Mapped[int] = mapped_column(primary_key=True)
    instance_name: Mapped[str] = mapped_column(String(255), unique=True)
    domain: Mapped[str] = mapped_column(String(255), index=True)
    public_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SystemLog(Base):
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[str] = mapped_column(String(32), index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    message: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(json_type(), default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
