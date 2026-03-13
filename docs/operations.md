# Operations

## CLI

- `openmailserver preflight`
- `openmailserver install`
- `openmailserver plan-dns`
- `openmailserver doctor`
- `openmailserver create-mailbox <local-part> <domain>`
- `openmailserver smoke-test`
- `openmailserver queue`
- `openmailserver backup-create`
- `openmailserver backup-verify`
- `openmailserver restore <path>`
- `openmailserver bootstrap`

## What `doctor` Checks

- required services and binaries
- generated runtime config presence
- database connectivity
- hostname and local config consistency
- relay-safety basics
- direct-delivery readiness

## Direct Delivery Requirements

`openmailserver` is direct-to-MX only. For internet delivery, the host needs:

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

## Data And Backups

Postgres stores control-plane data, outbound metadata, delivery events, and debug history.

Maildir stores inbound message files.

Backup and restore cover:

- Maildir
- attachments stored under `data/attachments`
- Postgres-backed control-plane data

Backup and restore do not currently capture runtime config under `runtime/`, generated
secret material such as `runtime/secrets.json`, or other host-level mail server state.
Copy those files separately if you need full-environment recovery.

## Troubleshooting

Start with:

```bash
openmailserver doctor
openmailserver queue
```

Useful debug endpoints:

- `GET /v1/debug/health`
- `GET /v1/debug/config`
- `GET /v1/debug/messages/{id}/trace`
- `GET /v1/debug/deliverability/report`
- `GET /v1/debug/logs`
- `GET /v1/queue`
