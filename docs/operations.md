# Operations

## CLI

- `openmailserver preflight`
- `openmailserver install --domain <domain> --hostname <mail-hostname>`
- `openmailserver plan-dns --public-ip <server-public-ip>`
- `openmailserver doctor`
- `openmailserver create-mailbox <local-part> <domain>`
- `openmailserver smoke-test`
- `openmailserver queue`
- `openmailserver backup-create`
- `openmailserver backup-verify`
- `openmailserver restore <path>`
- `openmailserver bootstrap`

## What `doctor` Checks

- Docker availability
- Docker Compose availability
- container runtime directory presence
- `mox` quickstart completion
- hostname and local config consistency
- relay-safety basics
- direct-delivery readiness

## Domain-First Verification

Open Mailserver is designed for the user to supply the real domain up front,
then verify the stack on the current machine while DNS is still being completed.

- set the real domain and canonical mail hostname during `openmailserver install`
- confirm `docker compose up`, `curl /health`, mailbox creation, and
  `openmailserver smoke-test`
- use `openmailserver plan-dns --public-ip <server-public-ip>` to finish the
  internet-facing setup

## Direct Delivery Requirements

Open Mailserver is direct-to-MX only. For internet delivery, the host needs:

- a static public IP
- outbound port `25`
- a canonical hostname such as `mail.example.com`
- forward DNS
- matching PTR / reverse DNS
- MX
- SPF
- DKIM
- DMARC
- TLS

Until those are complete, outbound mail may have poor deliverability or be
rejected, and inbound public mail may not arrive reliably.

If your provider does not let you change reverse DNS / `PTR`, treat that as a
real deployment limitation, not just a missing checkbox. The stack can still run
and receive some mail, but outbound direct-to-MX trust will suffer.

## Data And Backups

Postgres stores control-plane data, outbound metadata, delivery events, and debug history.

Maildir stores local control-plane copies, smoke-test data, and fallback artifacts
created by the app itself.

`mox` remains authoritative for hosted mailbox delivery and login state after
runtime sync.

Backup and restore cover:

- Maildir fallback data and app-managed local artifacts
- attachments stored under `data/attachments`
- Postgres-backed control-plane data
- `mox` runtime config, mailbox data, and web state under `runtime/mox/`
- encrypted runtime mailbox secrets

## Troubleshooting

Start with:

```bash
openmailserver doctor
openmailserver queue
docker compose ps
```

Hosted-domain notes:

- Additional hosted domains can be added by creating mailboxes at those domains.
- Local aliases are synced automatically into `mox`.
- External forwarding aliases are not currently supported by the `mox` runtime.

Useful debug endpoints:

- `GET /v1/debug/health`
- `GET /v1/debug/config`
- `GET /v1/debug/messages/{id}/trace`
- `GET /v1/debug/deliverability/report`
- `GET /v1/debug/logs`
- `GET /v1/queue`
