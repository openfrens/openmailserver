# DNS Setup

`openmailserver plan-dns` prints the records required for direct-to-MX delivery.

Minimum records:

- `A` or `AAAA` for the canonical mail hostname
- `MX` for the primary domain
- `SPF`
- `DKIM`
- `DMARC`
- matching `PTR` from the server IP back to the canonical hostname

The CLI intentionally separates easy local install from internet-ready direct-mail validation.
