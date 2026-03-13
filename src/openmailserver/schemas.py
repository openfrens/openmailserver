from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DomainCreate(BaseModel):
    name: str


class MailboxCreate(BaseModel):
    local_part: str
    domain: str
    password: str | None = None
    quota: int = 0


class AliasCreate(BaseModel):
    source: str
    destination: str


class AliasRead(BaseModel):
    id: int
    source: str
    destination: str


class SendMailRequest(BaseModel):
    sender: str
    recipients: list[str]
    subject: str
    text_body: str | None = None
    html_body: str | None = None
    cc: list[str] = Field(default_factory=list)
    bcc: list[str] = Field(default_factory=list)


class OutboundMessageRead(BaseModel):
    id: int
    sender: str
    recipients: list[str]
    subject: str
    state: str
    message_id: str | None
    queue_id: str | None
    error: str | None
    created_at: datetime
    sent_at: datetime | None

    model_config = {"from_attributes": True}


class MailboxRead(BaseModel):
    id: int
    email: str
    quota: int
    active: bool

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    key: str
    scopes: list[str]


class MailboxProvisionResponse(BaseModel):
    mailbox: MailboxRead
    password: str
    api_key: ApiKeyResponse


class MailboxMessageSummary(BaseModel):
    id: str
    subject: str | None = None
    from_address: str | None = Field(default=None, alias="from", serialization_alias="from")
    to: str | None = None
    date: str | None = None

    model_config = {"populate_by_name": True}


class MailboxMessageRead(MailboxMessageSummary):
    body: str


class QueueEntry(BaseModel):
    id: int
    state: str
    queue_id: str | None
    message_id: str | None
    error: str | None
    created_at: datetime


class HealthResponse(BaseModel):
    status: str
    platform: str
    checks: dict[str, str]


class DnsPlanResponse(BaseModel):
    hostname: str
    domain: str
    records: list[dict[str, str]]


class BackupResponse(BaseModel):
    path: str
    encrypted: bool


class DebugReport(BaseModel):
    status: str
    details: dict
