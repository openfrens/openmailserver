from __future__ import annotations

from email.message import EmailMessage
from types import SimpleNamespace

import pytest

from openmailserver.services import mailbox_reader_service


class _FakeImapSSL:
    def __init__(self, host, port, ssl_context, timeout):
        self.host = host
        self.port = port
        self.ssl_context = ssl_context
        self.timeout = timeout
        self.logged_in = None
        self.logged_out = False

    def login(self, address, password):
        self.logged_in = (address, password)
        return "OK", [b"logged in"]

    def select(self, mailbox_name, readonly=True):
        assert mailbox_name == "INBOX"
        assert readonly is True
        return "OK", [b"2"]

    def uid(self, command, *args):
        if command == "search":
            return "OK", [b"1 2"]
        if command == "fetch":
            message = EmailMessage()
            message["From"] = "sender@example.test"
            message["To"] = "agent@example.test"
            message["Subject"] = f"Hello {args[0]}"
            message["Date"] = "Fri, 13 Mar 2026 12:00:00 +0000"
            message.set_content(f"Body {args[0]}")
            return "OK", [(b"RFC822", message.as_bytes())]
        raise AssertionError((command, args))

    def logout(self):
        self.logged_out = True
        return "BYE", [b"logout"]


def test_list_messages_reads_live_imap_mailbox(monkeypatch):
    settings = SimpleNamespace(
        transport_mode="smtp",
        effective_imap_host="mox",
        imap_port=993,
        imap_security="ssl",
        imap_verify_tls=False,
        imap_timeout_seconds=9,
    )
    client = _FakeImapSSL("mox", 993, None, 9)

    monkeypatch.setattr(mailbox_reader_service, "get_settings", lambda: settings)
    monkeypatch.setattr(
        mailbox_reader_service,
        "mailbox_password_for",
        lambda address, _settings=None: "secret-pass",
    )
    monkeypatch.setattr(mailbox_reader_service.imaplib, "IMAP4_SSL", lambda **kwargs: client)

    messages = mailbox_reader_service.list_messages("agent@example.test")

    assert [message.id for message in messages] == ["2", "1"]
    assert messages[0].subject == "Hello 2"
    assert client.logged_in == ("agent@example.test", "secret-pass")
    assert client.logged_out is True


def test_get_message_reads_live_imap_mailbox(monkeypatch):
    settings = SimpleNamespace(
        transport_mode="smtp",
        effective_imap_host="mox",
        imap_port=993,
        imap_security="ssl",
        imap_verify_tls=False,
        imap_timeout_seconds=9,
    )
    client = _FakeImapSSL("mox", 993, None, 9)

    monkeypatch.setattr(mailbox_reader_service, "get_settings", lambda: settings)
    monkeypatch.setattr(
        mailbox_reader_service,
        "mailbox_password_for",
        lambda address, _settings=None: "secret-pass",
    )
    monkeypatch.setattr(mailbox_reader_service.imaplib, "IMAP4_SSL", lambda **kwargs: client)

    message = mailbox_reader_service.get_message("agent@example.test", "2")

    assert message is not None
    assert message.id == "2"
    assert message.subject == "Hello 2"
    assert "Body 2" in message.body


def test_reader_falls_back_to_maildir_without_live_password(monkeypatch):
    settings = SimpleNamespace(transport_mode="smtp")
    monkeypatch.setattr(mailbox_reader_service, "get_settings", lambda: settings)
    monkeypatch.setattr(
        mailbox_reader_service,
        "mailbox_password_for",
        lambda address, _settings=None: None,
    )
    monkeypatch.setattr(
        mailbox_reader_service,
        "list_maildir_messages",
        lambda address: [SimpleNamespace(id="local", subject="fallback")],
    )

    messages = mailbox_reader_service.list_messages("agent@example.test")

    assert messages[0].id == "local"


def test_reader_raises_when_imap_read_fails(monkeypatch):
    settings = SimpleNamespace(
        transport_mode="smtp",
        effective_imap_host="mox",
        imap_port=993,
        imap_security="ssl",
        imap_verify_tls=False,
        imap_timeout_seconds=9,
    )

    class _BrokenImap:
        def __init__(self, **kwargs):
            pass

        def login(self, address, password):
            raise mailbox_reader_service.imaplib.IMAP4.error("bad auth")

        def logout(self):
            return "BYE", [b"logout"]

    monkeypatch.setattr(mailbox_reader_service, "get_settings", lambda: settings)
    monkeypatch.setattr(
        mailbox_reader_service,
        "mailbox_password_for",
        lambda address, _settings=None: "secret-pass",
    )
    monkeypatch.setattr(mailbox_reader_service.imaplib, "IMAP4_SSL", lambda **kwargs: _BrokenImap())

    with pytest.raises(mailbox_reader_service.MailboxReadError, match="Unable to read mailbox"):
        mailbox_reader_service.list_messages("agent@example.test")
