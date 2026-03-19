# DNS Setup

`openmailserver plan-dns` prints the records required for direct-to-MX delivery.
`openmailserver domains status <domain>` also returns the same DNS plan alongside
the attached domain's readiness state.

Minimum records:

- `A` or `AAAA` for the canonical mail hostname
- `MX` for the primary domain
- `SPF`
- `DKIM`
- `DMARC`
- matching `PTR` from the server IP back to the canonical hostname

The CLI intentionally separates easy local install from internet-ready direct-mail validation.

For domains other than the configured primary domain, attach them first and then
explicitly verify that records have been applied before creating mailboxes:

```bash
.venv/bin/openmailserver domains attach example.net --dns-mode external
.venv/bin/openmailserver domains verify example.net --confirm-records
```

This is the main supported flow today: use a domain you already control, apply
the required DNS records, verify the domain, and then create mailboxes.
