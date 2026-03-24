# Security

Security defaults:

- installer-generated secrets
- zero default credentials
- API-key based auth with scopes
- redacted debug responses
- relay-safety checks
- encrypted backups for database and runtime state
- opaque identifiers for sensitive artifacts

Treat debug APIs, backups, outbound-mail persistence, and restored runtime state as
sensitive surfaces.
