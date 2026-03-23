# Open Mailserver

`openmailserver` is an open-source, self-hosted mail server control plane for agents. It helps you provision inboxes on infrastructure you control, using your own domain, through an HTTP API, a CLI, and a containerized mail runtime built around `mox`.

Website: [openmailserver.com](https://www.openmailserver.com) | License: MIT | Requires Python `3.11+`

## What Open Mailserver Is

Open Mailserver manages the control plane for a direct-to-MX mail server. The application handles mailbox provisioning, aliases, API keys, outbound mail metadata, backups, and debugging, while Docker Compose and `mox` provide the underlying mail runtime.

It includes:

- A FastAPI HTTP API for mailboxes, aliases, outbound mail, queue inspection, backups, DNS planning, and debugging.
- A Typer CLI for install, health checks, mailbox provisioning, queue inspection, backup, and restore workflows.
- A containerized `mox` runtime for SMTP, IMAP, and direct-to-MX delivery.
- `Postgres` storage for control-plane state and outbound metadata.
- `Maildir` storage for local mailbox contents.
- A checked-in Docker Compose deployment story.

Important operational constraints:

- `openmailserver` is designed for direct-to-MX mail delivery.
- For public internet delivery, the host needs a static public IP, outbound port `25`, forward and reverse DNS, `MX`, `SPF`, `DKIM`, `DMARC`, and `TLS`.
- `compose.yaml` is now the primary deployment path and includes the API, `Postgres`, and the `mox` runtime.
- For public internet delivery, prefer a Linux Docker host with direct access to ports `25`, `80`, and `443`.

## Quick Start

```bash
git clone https://github.com/openfrens/openmailserver
cd openmailserver
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
docker compose run --rm mox mox quickstart admin@example.com
docker compose up -d
.venv/bin/openmailserver doctor
```

The `install` command generates:

- `.env`
- Runtime directories for `mox`
- A `mox` quickstart seed file
- Container runtime guidance under `runtime/mox/`

Run `mox quickstart` once to create `runtime/mox/config/mox.conf` and
`runtime/mox/config/domains.conf`, then start the full stack with Docker Compose.

Then continue with:

```bash
.venv/bin/openmailserver plan-dns
.venv/bin/openmailserver create-mailbox agent example.com
.venv/bin/openmailserver smoke-test
curl http://127.0.0.1:8787/health
```

`openmailserver plan-dns` prints the DNS records required for direct-to-MX delivery. `openmailserver create-mailbox` provisions a mailbox and returns its credentials. `openmailserver smoke-test` prepares the local mailbox used for an initial smoke test.

## Common Commands

| Command | Purpose |
| --- | --- |
| `openmailserver preflight` | Run prerequisite checks. |
| `openmailserver install` | Generate `.env`, runtime directories, and `mox` setup guidance. |
| `openmailserver doctor` | Run direct-delivery readiness checks. |
| `openmailserver plan-dns` | Print the required DNS records. |
| `openmailserver create-mailbox <local-part> <domain>` | Provision a mailbox. |
| `openmailserver smoke-test` | Prepare the local smoke-test mailbox and workflow. |
| `openmailserver queue` | Show outbound queue state. |
| `openmailserver backup-create` | Create an encrypted backup archive. |
| `openmailserver backup-verify [path]` | Verify a backup archive. |
| `openmailserver restore <path>` | Restore a backup archive. |
| `openmailserver bootstrap` | Run `install` followed by `doctor`. |

## Configuration

Review `.env.example` and the generated `.env` before using the system beyond local setup. The most important settings are:

- `OPENMAILSERVER_DATABASE_URL`
- `OPENMAILSERVER_FALLBACK_DATABASE_URL`
- `OPENMAILSERVER_MAILDIR_ROOT`
- `OPENMAILSERVER_CANONICAL_HOSTNAME`
- `OPENMAILSERVER_PRIMARY_DOMAIN`
- `OPENMAILSERVER_PUBLIC_IP`
- `OPENMAILSERVER_ADMIN_API_KEY`
- `OPENMAILSERVER_BACKUP_ENCRYPTION_KEY`

## Development

```bash
make install
make run
make lint
make test
```

`make run` starts the FastAPI app on `0.0.0.0:8787`. The repository includes automated tests under `tests/`.

After `.env` exists, `compose.yaml` is the default way to run the API, `Postgres`, and the `mox` runtime together.

## Documentation

- [`docs/install.md`](docs/install.md)
- [`docs/api.md`](docs/api.md)
- [`docs/operations.md`](docs/operations.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/dns.md`](docs/dns.md)
- [`docs/security.md`](docs/security.md)
- [`docs/platforms.md`](docs/platforms.md)
- [`docs/runtime-removal-matrix.md`](docs/runtime-removal-matrix.md)

## License

MIT. See `LICENSE`.
