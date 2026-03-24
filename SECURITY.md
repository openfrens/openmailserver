# Security Policy

If you believe you have found a security vulnerability in Open Mailserver, do not
open a public issue for an actively exploitable report.

## Reporting

- Use GitHub private vulnerability reporting for the repository if it is enabled.
- If private reporting is not available, contact the maintainers privately before public disclosure.
- Include the affected commit or version, impact, reproduction steps, and any mitigations you have identified.

## Sensitive Areas

Treat these areas as especially sensitive when reviewing or reporting issues:

- mailbox authentication and API key handling
- debug endpoints and operational introspection
- backup archives and restore flows
- runtime secrets and encrypted credential storage
- direct-to-MX delivery configuration and DNS guidance

## Hardening Reference

Deployment defaults and operator guidance live in [`docs/security.md`](docs/security.md).
