# Open Mailserver

`openmailserver` is an open-source, self-hosted mail server control plane for agents. It helps you provision inboxes on infrastructure you control, using your own domain, through an HTTP API, a CLI, and generated `Postfix` and `Dovecot` configuration for native macOS and Linux hosts.

Website: [openmailserver.com](https://www.openmailserver.com) | License: MIT | Requires Python `3.11+`

## What Open Mailserver Is

Open Mailserver manages the control plane for a direct-to-MX mail server. The application handles mailbox provisioning, aliases, API keys, outbound mail metadata, backups, and debugging, while the generated runtime bundle and platform scripts help you install and manage the underlying mail stack on the host.

It includes:

- A FastAPI HTTP API for mailboxes, aliases, outbound mail, queue inspection, backups, DNS planning, and debugging.
- A Typer CLI for install, health checks, mailbox provisioning, queue inspection, backup, and restore workflows.
- Generated `Postfix` and `Dovecot` configuration.
- `Postgres` storage for control-plane state and outbound metadata.
- `Maildir` storage for local mailbox contents.
- Platform-specific runtime scripts for native Linux and macOS setup.

Important operational constraints:

- `openmailserver` is designed for direct-to-MX mail delivery.
- For public internet delivery, the host needs a static public IP, outbound port `25`, forward and reverse DNS, `MX`, `SPF`, `DKIM`, `DMARC`, and `TLS`.
- `Postfix` and `Dovecot` are not bundled inside the Python package; the generated platform scripts install and configure them on the host.
- `compose.yaml` is for the API and `Postgres` only, not a full mail-stack deployment.

## Quick Start

```bash
git clone https://github.com/openfrens/openmailserver
cd openmailserver
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
.venv/bin/openmailserver doctor
```

The `install` command generates:

- `.env`
- Runtime `Postfix` and `Dovecot` configuration
- SQL lookup files
- Platform-specific scripts under `runtime/scripts/`
- A service definition for running the API in the background

Run the generated scripts for your platform from `runtime/scripts/`.

Linux:

```bash
./runtime/scripts/install-mail-stack-linux.sh
./runtime/scripts/apply-config-linux.sh
./runtime/scripts/install-api-service-linux.sh
./runtime/scripts/status-api-service-linux.sh
```

macOS:

```bash
./runtime/scripts/install-mail-stack-macos.sh
./runtime/scripts/apply-config-macos.sh
./runtime/scripts/install-api-service-macos.sh
./runtime/scripts/status-api-service-macos.sh
```

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
| `openmailserver install` | Generate `.env`, runtime config, scripts, and a service definition. |
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

After `.env` exists, `compose.yaml` can also be used to run the API and `Postgres` for local control-plane development. It does not install or run the native mail stack.

## Documentation

- [`docs/install.md`](docs/install.md)
- [`docs/api.md`](docs/api.md)
- [`docs/operations.md`](docs/operations.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/dns.md`](docs/dns.md)
- [`docs/security.md`](docs/security.md)
- [`docs/platforms.md`](docs/platforms.md)

## License

MIT. See `LICENSE`.
