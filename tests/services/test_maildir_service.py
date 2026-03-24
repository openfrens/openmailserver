from __future__ import annotations

from email.message import EmailMessage
from types import SimpleNamespace

from openmailserver.services import maildir_service


def test_maildir_helpers_round_trip_message(monkeypatch, tmp_path):
    monkeypatch.setattr(
        maildir_service,
        "get_settings",
        lambda: SimpleNamespace(maildir_root=tmp_path / "maildir"),
    )

    message = EmailMessage()
    message["From"] = "sender@example.test"
    message["To"] = "agent@example.test"
    message["Subject"] = "Hello"
    message["Date"] = "Fri, 13 Mar 2026 12:00:00 +0000"
    message.set_content("Body")

    path = maildir_service.ensure_maildir("agent@example.test")
    message_id = maildir_service.deliver_local_copy("agent@example.test", message.as_bytes())
    messages = maildir_service.list_messages("agent@example.test")
    stored = maildir_service.get_message("agent@example.test", message_id)

    assert path == tmp_path / "maildir" / "example.test" / "agent"
    assert messages[0].subject == "Hello"
    assert stored is not None
    assert stored.body.strip() == "Body"


def test_get_message_returns_none_for_missing_id(monkeypatch, tmp_path):
    monkeypatch.setattr(
        maildir_service,
        "get_settings",
        lambda: SimpleNamespace(maildir_root=tmp_path / "maildir"),
    )

    assert maildir_service.get_message("agent@example.test", "missing") is None
