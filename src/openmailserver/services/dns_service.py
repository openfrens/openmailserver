from __future__ import annotations

from openmailserver.config import get_settings


def build_dns_plan(domain_name: str | None = None) -> list[dict[str, str]]:
    settings = get_settings()
    selector = "openmail"
    domain = domain_name or settings.primary_domain
    return [
        {"type": "A", "host": settings.canonical_hostname, "value": settings.public_ip},
        {
            "type": "MX",
            "host": domain,
            "value": f"10 {settings.canonical_hostname}.",
        },
        {"type": "TXT", "host": domain, "value": '"v=spf1 mx -all"'},
        {
            "type": "TXT",
            "host": f"{selector}._domainkey.{domain}",
            "value": '"v=DKIM1; k=rsa; p=<generated-public-key>"',
        },
        {
            "type": "TXT",
            "host": f"_dmarc.{domain}",
            "value": f'"v=DMARC1; p=none; rua=mailto:dmarc@{domain}"',
        },
        {"type": "PTR", "host": settings.public_ip, "value": settings.canonical_hostname},
    ]
