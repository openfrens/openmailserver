from __future__ import annotations


def test_list_domains_returns_bootstrapped_primary_domain(client, admin_headers):
    response = client.get("/v1/domains", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()[0]["domain"]["name"] == "example.test"


def test_attach_and_verify_domain_endpoints(client, admin_headers):
    attach_response = client.post(
        "/v1/domains/attach",
        json={
            "name": "external.test",
            "dns_mode": "external",
            "attach_source": "manual",
        },
        headers=admin_headers,
    )
    verify_response = client.post(
        "/v1/domains/external.test/verify",
        json={"confirmed_records": True},
        headers=admin_headers,
    )
    status_response = client.get("/v1/domains/external.test", headers=admin_headers)

    assert attach_response.status_code == 200
    assert verify_response.status_code == 200
    assert verify_response.json()["domain"]["verification_status"] == "verified"
    assert status_response.status_code == 200
    assert status_response.json()["domain"]["mailbox_ready"] is True
