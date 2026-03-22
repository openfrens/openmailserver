# Open Mailserver

`openmailserver` helps you run dedicated email inboxes for agents on infrastructure you control. Use your own domain for signups, verification, sending, and receiving mail, and manage the system through an HTTP API, a CLI, and generated `Postfix` and `Dovecot` configuration for native macOS and Linux hosts.

Website: [openmailserver.com](https://www.openmailserver.com) | License: MIT | Requires Python `3.11+`

## Why Use Open Mailserver

Open Mailserver is built for teams and builders who want agent-friendly email without handing mailbox control to a third party.

- Give each agent, bot, or workflow its own mailbox.
- Use a domain you already own.
- Keep the mail stack, data, and credentials under your control.
- Provision and operate mailboxes through code, scripts, or API calls.

## What You Get

This repository provides the control layer for a self-hosted mail server.

- A FastAPI HTTP API for mailboxes, aliases, outbound mail, queue inspection, backups, DNS planning, and debugging.
- A Typer CLI for install, health checks, mailbox provisioning, queue inspection, backup, and restore workflows.
- Generated `Postfix` and `Dovecot` configuration.
- `Postgres` storage for control-plane state and outbound metadata.
- `Maildir` storage for local mailbox contents.
- Platform-specific runtime scripts for native Linux and macOS setup.

In practice, that means you install the project, generate the runtime bundle, apply the generated host scripts, set up DNS, and then start creating mailboxes.

## Before You Start

- Open Mailserver is a self-hosted project for native macOS and Linux.
- It is designed for direct-to-MX delivery.
- For public internet delivery, the host needs a static public IP, outbound port `25`, forward and reverse DNS, `MX`, `SPF`, `DKIM`, `DMARC`, and `TLS`.
- `Postfix` and `Dovecot` are not bundled in the Python package; the generated platform scripts install and configure them on the host.
- `compose.yaml` runs only the API and `Postgres` for local development. It is not a full mail-stack deployment.

## Quick Start

### Install The Project

```bash
git clone https://github.com/openfrens/openmailserver
cd openmailserver
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/openmailserver install
.venv/bin/openmailserver doctor
```

The `install` command creates:

- `.env`
- Runtime `Postfix` and `Dovecot` configuration
- SQL lookup files
- Platform-specific scripts under `runtime/scripts/`
- A service definition for running the API in the background

### Apply The Generated Host Scripts

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

### Plan DNS And Create Your First Mailbox

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
| `openmailserver telemetry --disable` | Disable anonymous usage telemetry. |

## Key Configuration

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

After `.env` exists, `compose.yaml` can be used to run the API and `Postgres` for local control-plane development. It does not install or run the native mail stack.

## Documentation

- [`docs/install.md`](docs/install.md)
- [`docs/api.md`](docs/api.md)
- [`docs/operations.md`](docs/operations.md)
- [`docs/architecture.md`](docs/architecture.md)
- [`docs/dns.md`](docs/dns.md)
- [`docs/security.md`](docs/security.md)
- [`docs/platforms.md`](docs/platforms.md)

## Telemetry

Open Mailserver collects anonymous usage telemetry to help us understand how the project is used and prioritize improvements. Telemetry is **enabled by default** and can be disabled at any time.

### What is collected

- Event name (`cli_command`, `server_start`, `server_heartbeat`, `mailbox_created`)
- Which CLI command was run (just the name, no arguments or values)
- OS type, OS version, Python version
- Package version
- A random anonymous machine ID (UUID stored in `~/.openmailserver/telemetry_id`)

### What is NOT collected

- Email content, addresses, or domains
- IP addresses, hostnames, or DNS configuration
- API keys, passwords, or credentials
- Any personally identifiable information

### How to opt out

Any of these methods will disable telemetry:

```bash
# CLI command (persists across sessions)
openmailserver telemetry --disable

# Environment variable
export OPENMAILSERVER_TELEMETRY=false

# Cross-tool standard
export DO_NOT_TRACK=1
```

Telemetry is also automatically disabled in CI environments.

## License

MIT. See `LICENSE`.
