from __future__ import annotations

from fastapi.testclient import TestClient

from openmailserver.app import app


def test_magic_moment_flow(admin_headers):
    client = TestClient(app)
    mailbox = client.post(
        "/v1/mailboxes",
        json={"local_part": "magic", "domain": "example.test"},
        headers=admin_headers,
    )
    assert mailbox.status_code == 200
    mailbox_key = mailbox.json()["api_key"]["key"]

    send = client.post(
        "/v1/mail/send",
        json={
            "sender": "magic@example.test",
            "recipients": ["magic@example.test"],
            "subject": "magic moment",
            "text_body": "it works",
        },
        headers={"X-OpenMailserver-Key": mailbox_key},
    )
    assert send.status_code == 200

    sent = client.get("/v1/outbound", headers={"X-OpenMailserver-Key": mailbox_key})
    assert sent.status_code == 200
    assert sent.json()[0]["subject"] == "magic moment"

    inbox = client.get(
        "/v1/mailboxes/magic@example.test/messages",
        headers={"X-OpenMailserver-Key": mailbox_key},
    )
    assert inbox.status_code == 200
    assert any(message["subject"] == "magic moment" for message in inbox.json())
