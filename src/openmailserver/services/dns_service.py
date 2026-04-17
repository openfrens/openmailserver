from __future__ import annotations

from openmailserver.config import get_settings


def build_dns_plan(*, public_ip: str | None = None) -> list[dict[str, str]]:
    settings = get_settings()
    selector = "openmail"
    target_ip = public_ip or settings.public_ip
    return [
        {"type": "A", "host": settings.canonical_hostname, "value": target_ip},
        {
            "type": "MX",
            "host": settings.primary_domain,
            "value": f"10 {settings.canonical_hostname}.",
        },
        {
            "type": "CNAME",
            "host": f"autoconfig.{settings.primary_domain}",
            "value": f"{settings.canonical_hostname}.",
        },
        {
            "type": "CNAME",
            "host": f"mta-sts.{settings.primary_domain}",
            "value": f"{settings.canonical_hostname}.",
        },
        {"type": "TXT", "host": settings.primary_domain, "value": '"v=spf1 mx -all"'},
        {
            "type": "TXT",
            "host": f"{selector}._domainkey.{settings.primary_domain}",
            "value": '"v=DKIM1; k=rsa; p=<generated-public-key>"',
        },
        {
            "type": "TXT",
            "host": f"_dmarc.{settings.primary_domain}",
            "value": f'"v=DMARC1; p=none; rua=mailto:dmarc@{settings.primary_domain}"',
        },
        {"type": "PTR", "host": target_ip, "value": settings.canonical_hostname},
    ]
