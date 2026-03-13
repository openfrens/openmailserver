from __future__ import annotations

from types import SimpleNamespace

from openmailserver.services import dns_service


def test_build_dns_plan_uses_settings(monkeypatch):
    settings = SimpleNamespace(
        canonical_hostname="mail.example.test",
        primary_domain="example.test",
        public_ip="127.0.0.1",
    )
    monkeypatch.setattr(dns_service, "get_settings", lambda: settings)

    records = dns_service.build_dns_plan()

    assert [record["type"] for record in records] == ["A", "MX", "TXT", "TXT", "TXT", "PTR"]
    assert records[1]["value"] == "10 mail.example.test."
    assert records[-1]["value"] == "mail.example.test"
