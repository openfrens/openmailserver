# Security

Security defaults in V1:

- installer-generated secrets
- zero default credentials
- API-key based auth with scopes
- redacted debug responses
- relay-safety checks
- encrypted backup support
- opaque identifiers for sensitive artifacts

Treat debug APIs, backups, and outbound-mail persistence as sensitive surfaces.
