from __future__ import annotations


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_mailbox_and_send_mail(client, admin_headers):
    create_response = client.post(
        "/v1/mailboxes",
        json={"local_part": "agent", "domain": "example.test", "password": "secret-pass"},
        headers=admin_headers,
    )
    assert create_response.status_code == 200
    mailbox_key = create_response.json()["api_key"]["key"]

    send_response = client.post(
        "/v1/mail/send",
        json={
            "sender": "agent@example.test",
            "recipients": ["agent@example.test"],
            "subject": "hello",
            "text_body": "world",
        },
        headers={"X-OpenMailserver-Key": mailbox_key},
    )
    assert send_response.status_code == 200
    assert send_response.json()["state"] in {"sent", "queued"}

    list_response = client.get(
        "/v1/mailboxes/agent@example.test/messages",
        headers={"X-OpenMailserver-Key": mailbox_key},
    )
    assert list_response.status_code == 200
    assert len(list_response.json()) >= 1


def test_debug_and_backup_endpoints(client, admin_headers):
    debug_response = client.get("/v1/debug/config", headers=admin_headers)
    assert debug_response.status_code == 200
    assert debug_response.json()["details"]["admin_api_key"] == "***configured***"

    backup_response = client.post("/v1/backup", headers=admin_headers)
    assert backup_response.status_code == 200
    assert backup_response.json()["encrypted"] is True

    validate_response = client.post(
        "/v1/restore/validate",
        headers=admin_headers,
        params={"path": backup_response.json()["path"]},
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["status"] == "ok"
